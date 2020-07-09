import base64
import re
import urllib.parse

from datetime import datetime, timedelta
from hashlib import sha1
import hmac

from basic_models.models import CreatedUpdatedBy, CreatedUpdatedAt, IsActive
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.utils import timezone
from oauthlib.common import generate_token

import cachemodel
from django.db.models import Manager
from django.utils.deconstruct import deconstructible
from oauth2_provider.models import AccessToken, Application, RefreshToken
from rest_framework.authtoken.models import Token

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class EmailBlacklist(models.Model):
    email = models.EmailField(unique=True)

    class Meta:
        verbose_name = 'Blacklisted email'
        verbose_name_plural = 'Blacklisted emails'

    @staticmethod
    def generate_email_signature(email, badgrapp_pk=None):
        secret_key = settings.UNSUBSCRIBE_SECRET_KEY

        expiration = datetime.utcnow() + timedelta(days=7)  # In one week.
        timestamp = int((expiration - datetime(1970, 1, 1)).total_seconds())

        email_encoded = base64.b64encode(email.encode('utf-8'))
        hashed = hmac.new(secret_key.encode('utf-8'), email_encoded + str(timestamp).encode('utf-8'), sha1)

        if badgrapp_pk is None:
            badgrapp_pk = BadgrApp.objects.get_by_id_or_default().pk

        return reverse('unsubscribe', kwargs={
            'email_encoded': email_encoded,
            'expiration': timestamp,
            'signature': hashed.hexdigest(),
        }) + '?a={}'.format(badgrapp_pk)

    @staticmethod
    def verify_email_signature(email_encoded, expiration, signature):
        secret_key = settings.UNSUBSCRIBE_SECRET_KEY

        hashed = hmac.new(secret_key, email_encoded + expiration, sha1)
        return hmac.compare_digest(hashed.hexdigest(), str(signature))


class BadgrAppManager(Manager):
    def get_current(self, request=None, raise_exception=False):
        """
        A safe method for getting the current BadgrApp related to a request. It will always return a BadgrApp if
        the server is properly configured.
        :param request: Django Request object
        :param raise_exception: bool
        :return: BadgrApp
        """
        origin = None
        existing_session_app_id = None

        if request:
            if request.META.get('HTTP_ORIGIN'):
                origin = request.META.get('HTTP_ORIGIN')
            elif request.META.get('HTTP_REFERER'):
                origin = request.META.get('HTTP_REFERER')
            existing_session_app_id = request.session.get('badgr_app_pk', None)

        if existing_session_app_id:
            try:
                return self.get(id=existing_session_app_id)
            except self.model.DoesNotExist:
                pass

        if origin:
            url = urllib.parse.urlparse(origin)
            try:
                return self.get(cors=url.netloc)
            except self.model.DoesNotExist:
                pass
        if raise_exception:
            return self.get(is_default=True)
        else:
            return self.get_by_id_or_default()

    def get_by_id_or_default(self, badgrapp_id=None):
        if badgrapp_id:
            try:
                return self.get(id=badgrapp_id)
            except (self.model.DoesNotExist, ValueError,):
                pass
        try:
            return self.get(is_default=True)
        except (self.model.DoesNotExist, self.model.MultipleObjectsReturned,):
            badgrapp = None
            legacy_default_setting = getattr(settings, 'BADGR_APP_ID', None)
            if legacy_default_setting is not None:
                try:
                    badgrapp = self.get(id=legacy_default_setting)
                except self.model.DoesNotExist:
                    pass
            else:
                badgrapp = self.first()

            if badgrapp is not None:
                badgrapp.is_default = True
                badgrapp.save()
                return badgrapp

            # failsafe: return a new entry if there are none
            return self.create(
                cors='localhost:81',
                is_default=True,
                signup_redirect='http://localhost:81/signup'
            )
        except self.model.MultipleObjectsReturned:
            badgrapp = self.filter(is_default=True).first()
            badgrapp.save()  # trigger one-default-only setting
            return badgrapp


class BadgrApp(CreatedUpdatedBy, CreatedUpdatedAt, IsActive, cachemodel.CacheModel):
    name = models.CharField(max_length=254)
    cors = models.CharField(max_length=254, unique=True)
    is_default = models.BooleanField(default=False)
    email_confirmation_redirect = models.URLField()
    signup_redirect = models.URLField()
    forgot_password_redirect = models.URLField()
    ui_login_redirect = models.URLField(null=True)
    ui_signup_success_redirect = models.URLField(null=True)
    ui_connect_success_redirect = models.URLField(null=True)
    ui_signup_failure_redirect = models.URLField(null=True)
    public_pages_redirect = models.URLField(null=True)
    oauth_authorization_redirect = models.URLField(null=True)
    use_auth_code_exchange = models.BooleanField(default=False)
    oauth_application = models.ForeignKey("oauth2_provider.Application", null=True, blank=True)

    objects = BadgrAppManager()

    PROPS_FOR_DEFAULT = [
        'forgot_password_redirect', 'ui_login_redirect', 'ui_signup_success_redirect', 'ui_connect_success_redirect',
        'ui_signup_failure_redirect', 'oauth_authorization_redirect', 'email_confirmation_redirect'
    ]

    def __str__(self):
        return self.cors

    def get_path(self, path='/', use_https=None):
        if use_https is None:
            use_https = self.signup_redirect.startswith('https')
        scheme = 'https://' if use_https else 'http://'
        return '{}{}{}'.format(scheme, self.cors, path)

    @property
    def oauth_application_client_id(self):
        if self.oauth_application is None:
            return None
        return self.oauth_application.client_id

    @oauth_application_client_id.setter
    def oauth_application_client_id(self, value):
        # Allows setting of OAuth Application foreign key by client_id. Raises Application.DoesNotExist when not found
        # This does not save the record, so .save() must be called as appropriate.
        if value is None:
            self.oauth_application = None
        else:
            self.oauth_application = Application.objects.get(client_id=value)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other BadgrApp instances as no longer the default.
            self.__class__.objects.filter(is_default=True).exclude(id=self.pk).update(is_default=False)
        else:
            if not self.__class__.objects.filter(is_default=True).exists():
                self.is_default = True

        for prop in self.PROPS_FOR_DEFAULT:
            if not getattr(self, prop):
                setattr(self, prop, self.signup_redirect)
        return super(BadgrApp, self).save(*args, **kwargs)


@deconstructible
class DefinedScopesValidator(object):
    message = "Does not match defined scopes"
    code = 'invalid'

    def __call__(self, value):
        defined_scopes = set(getattr(settings, 'OAUTH2_PROVIDER', {}).get('SCOPES', {}).keys())
        provided_scopes = set(s.strip() for s in re.split(r'[\s\n]+', value))
        if provided_scopes - defined_scopes:
            raise ValidationError(self.message, code=self.code)
        pass

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class ApplicationInfo(cachemodel.CacheModel):
    application = models.OneToOneField('oauth2_provider.Application')
    icon = models.FileField(blank=True, null=True)
    name = models.CharField(max_length=254, blank=True, null=True, default=None)
    website_url = models.URLField(blank=True, null=True, default=None)
    allowed_scopes = models.TextField(blank=False, validators=[DefinedScopesValidator()])
    trust_email_verification = models.BooleanField(default=False)

    def get_visible_name(self):
        if self.name:
            return self.name
        return self.application.name

    def get_icon_url(self):
        if self.icon:
            return self.icon.url

    @property
    def scope_list(self):
        return [s for s in re.split(r'[\s\n]+', self.allowed_scopes) if s]


class AccessTokenProxyManager(models.Manager):

    def generate_new_token_for_user(self, user, scope='r:profile', application=None, expires=None, refresh_token=False):
        with transaction.atomic():
            if application is None:
                application, created = Application.objects.get_or_create(
                    client_id='public',
                    client_type=Application.CLIENT_PUBLIC,
                    authorization_grant_type=Application.GRANT_PASSWORD,
                )
                if created:
                    ApplicationInfo.objects.create(application=application)

            if expires is None:
                access_token_expires_seconds = getattr(settings, 'OAUTH2_PROVIDER', {}).get(
                    'ACCESS_TOKEN_EXPIRE_SECONDS', 86400)
                expires = timezone.now() + timezone.timedelta(seconds=access_token_expires_seconds)

            accesstoken = self.create(
                application=application,
                user=user,
                expires=expires,
                token=generate_token(),
                scope=scope
            )

            if refresh_token:
                accesstoken.refresh_token = RefreshToken.objects.create(
                    access_token=accesstoken,
                    user=user,
                    application=application,
                    token=generate_token()
                )

        return accesstoken

    def get_from_entity_id(self, entity_id):
        # lookup by a faked
        padding = len(entity_id) % 4
        if padding > 0:
            entity_id = '{}{}'.format(entity_id, (4 - padding) * '=')
        decoded = str(base64.urlsafe_b64decode(entity_id.encode('utf-8')), 'utf-8')
        id = re.sub(r'^{}'.format(self.model.fake_entity_id_prefix), '', decoded)
        try:
            pk = int(id)
        except ValueError as e:
            raise self.model.DoesNotExist()

        return self.get(pk=pk)


class AccessTokenProxy(AccessToken):
    objects = AccessTokenProxyManager()
    fake_entity_id_prefix = "AccessTokenProxy.id="

    class Meta:
        proxy = True
        verbose_name = 'access token'
        verbose_name_plural = 'access tokens'

    def revoke(self):
        RefreshToken.objects.filter(access_token=self.pk).delete()
        self.delete()

    @property
    def entity_id(self):
        # fake an entityId for this non-entity
        digest = "{}{}".format(self.fake_entity_id_prefix, self.pk)
        b64_string = str(base64.urlsafe_b64encode(digest.encode('utf-8')), 'utf-8')
        b64_trimmed = re.sub(r'=+$', '', b64_string)
        return b64_trimmed

    def get_entity_class_name(self):
        return 'AccessToken'

    @property
    def application_name(self):
        return self.application.name

    @property
    def applicationinfo(self):
        try:
            return self.application.applicationinfo
        except ApplicationInfo.DoesNotExist:
            return ApplicationInfo()

    def __str__(self):
        return self.obscured_token

    @property
    def obscured_token(self):
        if self.token:
            return "{}***".format(self.token[:4])

    @property
    def seconds_to_expiration(self):
        valid_for = self.expires - timezone.now()
        return int(round(valid_for.total_seconds()))


class AccessTokenScope(models.Model):
    token = models.ForeignKey(AccessToken)
    scope = models.CharField(max_length=255)

    class Meta:
        unique_together = ['token', 'scope']

    def __str__(self):
        return self.scope


class LegacyTokenProxy(Token):
    class Meta:
        proxy = True
        verbose_name = 'Legacy token'
        verbose_name_plural = 'Legacy tokens'

    def __str__(self):
        return self.obscured_token

    @property
    def obscured_token(self):
        if self.key:
            return "{}***".format(self.key[:4])
