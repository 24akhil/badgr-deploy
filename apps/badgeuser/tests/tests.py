import random
import re

import os

from allauth.account.models import EmailConfirmation
from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import override_settings
from django.utils import timezone

from mainsite import TOP_DIR
from rest_framework.authtoken.models import Token

from badgeuser.models import (
    BadgeUser, UserRecipientIdentifier, EmailAddressVariant, CachedEmailAddress, TermsVersion)
from badgeuser.serializers_v1 import BadgeUserProfileSerializerV1
from badgeuser.serializers_v2 import BadgeUserSerializerV2
from issuer.models import BadgeClass, Issuer
from mainsite.models import BadgrApp, ApplicationInfo, AccessTokenProxy
from mainsite.tests.base import BadgrTestCase, SetupIssuerHelper
from mainsite.utils import backoff_cache_key



class AuthTokenTests(BadgrTestCase):

    def test_create_user_auth_token(self):
        """
        Ensure that get can create a token for a user that doesn't have one
        and that it doesn't modify a token for a user that already has one.
        """

        self.setup_user(authenticate=True)

        response = self.client.get('/v1/user/auth-token')
        self.assertEqual(response.status_code, 200)
        token = response.data.get('token')
        self.assertRegex(token, r'[\da-f]{40}')

        second_response = self.client.get('/v1/user/auth-token')
        self.assertEqual(token, second_response.data.get('token'))

    def test_update_user_auth_token(self):
        """
        Ensure that a PUT request updates a user token.
        """
        # Create a token for the first time.
        user = self.setup_user(authenticate=True)

        response = self.client.get('/v1/user/auth-token')
        self.assertEqual(response.status_code, 200)
        token = response.data.get('token')
        self.assertRegex(token, r'[\da-f]{40}')

        # Ensure that token has changed.
        second_response = self.client.put('/v1/user/auth-token')
        self.assertNotEqual(token, second_response.data.get('token'))
        self.assertTrue(second_response.data.get('replace'))

        self.assertEqual(user.cached_token(), second_response.data.get('token'))
        self.assertEqual(Token.objects.get(user=user).key, user.cached_token())


class UserCreateTests(BadgrTestCase):
    def test_create_user(self):
        user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'newuniqueuser1@example.com',
            'password': 'secr3t4nds3cur3'
        }

        self.badgr_app.email_confirmation_redirect = 'http://test-badgr-ui.example.com/profile/'
        self.badgr_app.save()

        response = self.client.post('/v1/user/profile', user_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("signup=true", mail.outbox[0].body)
        self.assertNotIn("source=mozilla", mail.outbox[0].body)

        launch_url = re.search("(?P<url>/v1/[^\s]+)", mail.outbox[0].body).group("url")
        response = self.client.get(launch_url)
        self.assertEqual(response.status_code, 302)
        redirect_url = response._headers['location'][1]

        self.assertIn('/welcome', redirect_url)


    def test_create_user_from_mozilla(self):
        user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'mozillauser@example.com',
            'password': 'secr3t4nds3cur3',
            'source': 'mozilla'
        }

        response = self.client.post('/v1/user/profile', user_data)

        self.assertEqual(response.status_code, 201)
        self.assertIn("source=mozilla", mail.outbox[0].body)
        self.assertIn("signup=true", mail.outbox[0].body)

    def test_user_can_add_secondary_email_without_welcome_query_param(self):
        email = "unclaimed3@example.com"
        first_user = self.setup_user(authenticate=False)
        CachedEmailAddress.objects.create(user=first_user, email=email, primary=False, verified=False)
        second_user = self.setup_user(email='second@user.fake', authenticate=True)
        response = self.client.post('/v1/user/emails', {'email': email})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("signup=true", mail.outbox[0].body)

    def test_create_user_with_already_claimed_email(self):
        email = 'test2@example.com'
        user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': email,
            'password': '123456'
        }
        existing_user = self.setup_user(email=email, authenticate=False, create_email_address=True)

        response = self.client.post('/v1/user/profile', user_data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_can_create_user_with_preexisting_unconfirmed_email(self):
        email = 'unclaimed1@example.com'
        user_data = {
            'first_name': 'NEW Test',
            'last_name': 'User',
            'email': email,
            'password': 'secr3t4nds3cur3'
        }

        # create an existing user that owns email -- but unverified
        existing_user = self.setup_user(email=email, password='secret', authenticate=False, verified=False)
        existing_user_pk = existing_user.pk
        existing_email = existing_user.cached_emails()[0]
        self.assertEqual(existing_email.email, email)
        self.assertFalse(existing_email.verified)

        # attempt to signup with the same email
        response = self.client.post('/v1/user/profile', user_data)

        # should work successfully and a confirmation email  sent
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        # the user with this email should be the new signup
        new_user = BadgeUser.objects.get(email=email)
        self.assertEqual(new_user.email, email)
        self.assertEqual(new_user.first_name, user_data.get('first_name'))
        self.assertEqual(new_user.last_name, user_data.get('last_name'))
        existing_email = CachedEmailAddress.objects.get(email=email)
        self.assertEqual(existing_email.user, new_user)

        # the old user should no longer exist
        with self.assertRaises(BadgeUser.DoesNotExist):
            old_user = BadgeUser.objects.get(pk=existing_user_pk)

    def test_user_can_add_secondary_email_of_preexisting_unclaimed_email(self):
        email = "unclaimed2@example.com"
        first_user = self.setup_user(authenticate=False)
        CachedEmailAddress.objects.create(user=first_user, email=email, primary=False, verified=False)

        second_user = self.setup_user(email='second@user.fake', authenticate=True)
        response = self.client.post('/v1/user/emails', {'email': email})
        self.assertEqual(response.status_code, 201)

    def test_can_create_account_with_same_email_since_deleted(self):
        email = 'unclaimed1@example.com'
        new_email = 'newjunkeremail@junk.net'
        first_user_data = user_data = {
            'first_name': 'NEW Test',
            'last_name': 'User',
            'email': email,
            'password': 'secr3t4nds3cur3'
        }
        response = self.client.post('/v1/user/profile', user_data)

        first_user = BadgeUser.objects.get(email=email)
        first_email = CachedEmailAddress.objects.get(email=email)
        first_email.verified = True
        first_email.save()

        second_email = CachedEmailAddress(email=new_email, user=first_user, verified=True)
        second_email.save()

        self.assertEqual(len(first_user.cached_emails()), 2)

        self.client.force_authenticate(user=first_user)
        response = self.client.put(
            reverse('v1_api_user_email_detail', args=[second_email.pk]),
            {'primary': True}
        )
        self.assertEqual(response.status_code, 200)

        # Reload user and emails
        first_user = BadgeUser.objects.get(email=new_email)
        first_email = CachedEmailAddress.objects.get(email=email)
        second_email = CachedEmailAddress.objects.get(email=new_email)

        self.assertEqual(first_user.email, new_email)
        self.assertTrue(second_email.primary)
        self.assertFalse(first_email.primary)

        self.assertTrue(email in [e.email for e in first_user.cached_emails()])
        first_email.delete()
        self.assertFalse(email in [e.email for e in first_user.cached_emails()])

        user_data['name'] = 'NEWEST Test'
        self.client.force_authenticate(user=None)
        response = self.client.post('/v1/user/profile', user_data)

        self.assertEqual(response.status_code, 201)

    def test_shouldnt_error_when_user_exists_with_email(self):
        email = 'existing3@example.test'

        old_user = self.setup_user(email=email, password='secret2')  # password is set because its an existing user

        response = self.client.post('/v1/user/profile', {
            'first_name': 'existing',
            'last_name': 'user',
            'password': 'secret',
            'email': email
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_autocreated_user_can_signup(self):
        email = 'existing4@example.test'

        old_user = self.setup_user(email=email, password=None, create_email_address=False)  # no password set

        response = self.client.post('/v1/user/profile', {
            'first_name': 'existing',
            'last_name': 'user',
            'password': 'secr3t4nds3cur3',
            'email': email
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

    def test_should_signup_with_email_with_plus(self):
        response = self.client.post('/v1/user/profile', {
            'first_name': 'existing',
            'last_name': 'user',
            'password': 'secr3t4nds3cur3',
            'email': 'nonexistent23+extra@test.nonexistent'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

    def test_should_signup_with_email_with_uc_email(self):
        response = self.client.post('/v1/user/profile', {
            'first_name': 'existing',
            'last_name': 'user',
            'password': 'secr3t4nds3cur3',
            'email': 'VERYNONEXISTENT@test.nonexistent'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

    def test_autocreated_user_signup(self):
        """
        Sometimes admins have a need to manually create users and grant them auth tokens
        where their primary email is marked verified, but no password is set. For these
        users, the signup flow should proceed normally.
        """
        badgrapp = BadgrApp.objects.first()
        badgrapp.ui_login_redirect = 'http://testui.test/auth/login/'
        badgrapp.email_confirmation_redirect = 'http://testui.test/auth/login/'
        badgrapp.save()

        user = BadgeUser(
            email='testuser123@example.test'
        )
        user.save()
        email = CachedEmailAddress.cached.create(user=user, email=user.email, verified=True)

        user_data = {
            'first_name': 'Usery',
            'last_name': 'McUserface',
            'password': 'secr3t4nds3cur3',
            'email': user.email
        }
        response = self.client.post('/v1/user/profile', user_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        verify_url = re.search("(?P<url>/v2/[^\s]+)", mail.outbox[0].body).group("url")
        response = self.client.get(verify_url[:-5])
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(user_data['first_name'], response._headers['location'][1])

        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(user_data['first_name'], response._headers['location'][1])

        user = BadgeUser.cached.get(email=user.email)
        self.assertIsNotNone(user.password)

        self.client.logout()
        self.client.login(username=user.username, password=user_data['password'])
        response = self.client.get('/v1/user/profile')
        self.assertEqual(response.data['first_name'], user_data['first_name'])


class UserUnitTests(BadgrTestCase):
    def test_user_can_have_unicode_characters_in_name(self):
        user = BadgeUser(
            username='abc', email='abc@example.com',
            first_name='\xe2', last_name='Bowie')

        self.assertEqual(user.get_full_name(), '\xe2 Bowie')


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
)
class UserEmailTests(BadgrTestCase):
    def setUp(self):
        super(UserEmailTests, self).setUp()

        self.badgr_app = BadgrApp(cors='testserver',
                                  email_confirmation_redirect='http://testserver/login/',
                                  forgot_password_redirect='http://testserver/reset-password/')
        self.badgr_app.save()

        self.first_user_email = 'first.user@newemail.test'
        self.first_user_email_secondary = 'first.user+2@newemail.test'
        self.first_user = self.setup_user(email=self.first_user_email, authenticate=True)
        CachedEmailAddress.objects.create(user=self.first_user, email=self.first_user_email_secondary, verified=True)
        response = self.client.get('/v1/user/auth-token')
        self.assertEqual(response.status_code, 200)

    def test_user_register_new_email(self):
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        starting_count = len(response.data)

        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(starting_count+1, len(response.data))

        # Mark email as verified
        email = CachedEmailAddress.cached.get(email='new+email@newemail.com')
        email.verified = True
        email.save()

        # Can not add the same email twice
        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue("Could not register email address." in response.data)

    def test_user_can_verify_new_email(self):
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        starting_count = len(response.data)

        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(starting_count+1, len(response.data))

        # Mark email as verified
        email = CachedEmailAddress.cached.get(email='new+email@newemail.com')
        self.assertEqual(len(mail.outbox), 1)
        verify_url = re.search("(?P<url>/v1/[^\s]+)", mail.outbox[0].body).group("url")
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)

        email = CachedEmailAddress.cached.get(email='new+email@newemail.com')
        self.assertTrue(email.verified)

    def test_user_cant_register_new_email_verified_by_other(self):
        second_user = self.setup_user(authenticate=False)
        existing_mail = CachedEmailAddress.objects.create(
            user=self.first_user, email='new+email@newemail.com', verified=True)

        response = self.client.get('/v1/user/emails')

        self.assertEqual(response.status_code, 200)
        starting_count = len(response.data)

        # Another user tries to add this email
        self.client.force_authenticate(user=second_user)
        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 400)

        self.client.force_authenticate(user=self.first_user)
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(starting_count, len(response.data))

    def test_user_can_remove_email(self):
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)

        not_primary = random.choice([e for e in response.data if e['verified'] and not e['primary']])
        primary = random.choice([e for e in response.data if e['primary']])

        # cant remove primary email
        response = self.client.delete('/v1/user/emails/{}'.format(primary.get('id')))
        self.assertEqual(response.status_code, 400)
        response = self.client.get('/v1/user/emails/{}'.format(primary.get('id')))
        self.assertEqual(response.status_code, 200)

        # can remove a non-primary email
        response = self.client.delete('/v1/user/emails/{}'.format(not_primary.get('id')))
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/v1/user/emails/{}'.format(not_primary.get('id')))
        self.assertEqual(response.status_code, 404)

    def test_user_can_make_email_primary(self):
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)

        self.assertGreater(len(response.data), 0)

        not_primary = random.choice([e for e in response.data if e['verified'] and not e['primary']])

        # set a non primary email to primary
        response = self.client.put('/v1/user/emails/{}'.format(not_primary.get('id')), {
            'primary': True
        })
        self.assertEqual(response.status_code, 200)

        # confirm that the new email is primary and the others aren't
        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        for email in response.data:
            if email['id'] == not_primary['id']:
                self.assertEqual(email['primary'], True)
            else:
                self.assertEqual(email['primary'], False)

    def test_user_can_resend_verification_email(self):
        # register a new un-verified email
        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        not_verified = random.choice([e for e in response.data if not e['verified']])
        verified = random.choice([e for e in response.data if e['verified']])

        # dont resend verification email if already verified
        response = self.client.put('/v1/user/emails/{}'.format(verified.get('id')), {
            'resend': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # gets an email for an unverified email
        response = self.client.put('/v1/user/emails/{}'.format(not_verified.get('id')), {
            'resend': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_no_login_on_confirmation_of_verified_email(self):
        # register a new un-verified email
        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)

        # receive verification email
        self.assertEqual(len(mail.outbox), 1)
        verify_url = re.search("(?P<url>/v1/[^\s]+)", mail.outbox[0].body).group("url")

        # verify the email address
        email_address = CachedEmailAddress.objects.filter(verified=False).get()
        email_address.verified = True
        email_address.save()

        # verification attempt fails
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('authError', response['location'])
        self.assertNotIn('authToken', response['location'])

    def test_verification_cannot_be_reused(self):
        # register a new un-verified email
        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)

        # receive verification email
        self.assertEqual(len(mail.outbox), 1)
        verify_url = re.search("(?P<url>/v1/[^\s]+)", mail.outbox[0].body).group("url")

        # verify the email address successfully
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('authToken', response['location'])
        self.assertNotIn('authError', response['location'])

        # second verification attempt fails
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('authError', response['location'])
        self.assertNotIn('authToken', response['location'])

    def test_user_can_request_forgot_password(self):
        self.client.logout()
        cache.clear()

        # dont send recovery to unknown emails
        response = self.client.post('/v1/user/forgot-password', {
            'email': 'unknown-test2@example.com.fake',
        })
        self.assertEqual(response.status_code, 200, "Does not leak information about account emails")
        self.assertEqual(len(mail.outbox), 0)

        # successfully send recovery email
        response = self.client.post('/v1/user/forgot-password', {
            'email': self.first_user_email
        })

        backoff_key = backoff_cache_key(self.first_user_email, None)
        backoff_data = {'count': 6, 'until': timezone.now() + timezone.timedelta(seconds=60)}
        cache.set(backoff_key, backoff_data)
        self.assertEqual(cache.get(backoff_key), backoff_data)

        self.assertEqual(response.status_code, 200)
        # received email with recovery url
        self.assertEqual(len(mail.outbox), 1)
        matches = re.search(r'/v1/user/forgot-password\?token=([-0-9a-zA-Z]*)', mail.outbox[0].body)
        self.assertIsNotNone(matches)
        token = matches.group(1)
        new_password = 'new-password-ee'

        # able to use token received in email to reset password
        response = self.client.put('/v1/user/forgot-password', {
            'token': token,
            'password': new_password
        })
        self.assertEqual(response.status_code, 200)

        backoff_data = cache.get(backoff_key)
        self.assertIsNone(backoff_data)

        response = self.client.post('/api-auth/token', {
            'username': self.first_user.username,
            'password': new_password,
        })
        self.assertEqual(response.status_code, 200)

    def test_lower_variant_autocreated_on_new_email(self):
        first_email = CachedEmailAddress(
            email="HelloAgain@world.com", user=BadgeUser.objects.first(), verified=True
        )
        first_email.save()
        self.assertIsNotNone(first_email.pk)

        variants = EmailAddressVariant.objects.filter(canonical_email=first_email)

        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].email, 'helloagain@world.com')

    def test_can_create_new_variant_api(self):
        user = BadgeUser.objects.first()
        first_email = CachedEmailAddress(
            email="helloagain@world.com", user=user, verified=True
        )
        first_email.save()
        self.assertIsNotNone(first_email.pk)

        self.client.force_authenticate(user=user)
        response = self.client.post('/v1/user/emails', {'email': 'HelloAgain@world.com'})

        self.assertEqual(response.status_code, 400)
        self.assertTrue('Matching address already exists. New case variant registered.' in response.data)

        variants = first_email.cached_variants()
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].email, 'HelloAgain@world.com')

    def test_can_create_variants(self):
        user = self.setup_user(authenticate=False)
        first_email = CachedEmailAddress.objects.create(email="test@example.com", verified=True, user=user)
        self.assertIsNotNone(first_email.pk)

        first_variant_email = "TEST@example.com"
        second_variant_email = "Test@example.com"

        first_variant = EmailAddressVariant(email=first_variant_email, canonical_email=first_email)
        first_variant.save()
        self.assertEqual(first_variant.canonical_email, first_email)

        second_variant = first_email.add_variant(second_variant_email)
        self.assertEqual(second_variant.canonical_email, first_email)

        self.assertEqual(len(first_email.emailaddressvariant_set.all()), 2)
        self.assertEqual(len(first_email.cached_variants()), 2)

    def test_user_can_create_variant_method(self):
        user = BadgeUser.objects.first()
        first_email = CachedEmailAddress(
            email="howdy@world.com", user=user, verified=True
        )
        first_email.save()
        first_email.add_variant("HOWDY@world.com")

        self.assertTrue(user.can_add_variant("Howdy@world.com"))
        self.assertFalse(user.can_add_variant("HOWDY@world.com"))  # already exists
        self.assertFalse(user.can_add_variant("howdy@world.com"))  # is the original
        self.assertFalse(user.can_add_variant("howdyfeller@world.com"))  # not a match of original

    def test_can_create_variant_for_unconfirmed_email(self):
        user = BadgeUser.objects.first()
        new_email_address = "new@unconfirmed.info"
        new_email = CachedEmailAddress.objects.create(email=new_email_address, user=user)
        new_variant = EmailAddressVariant(email=new_email_address.upper(), canonical_email=new_email)

        new_variant.save()
        self.assertFalse(new_variant.verified)

        verified_emails = [e.email for e in user.emailaddress_set.filter(verified=True)] \
                          + [e.email for e in user.cached_email_variants() if e.verified]

        self.assertTrue(new_variant not in verified_emails)

    def cannot_link_variant_of_case_insensitive_nonmatch(self):
        first_email = CachedEmailAddress.objects.get(email="test@example.com")
        self.assertIsNotNone(first_email.pk)

        variant_email = "NOMATCH@example.com"

        variant = EmailAddressVariant(email=variant_email, canonical_email=first_email)
        try:
            variant.save()
        except ValidationError as e:
            self.assertEqual(e.message, "New EmailAddressVariant does not match stored email address.")
        else:
            raise self.fail("ValidationError expected on nonmatch.")


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
)
class UserRecipientIdentifierTests(SetupIssuerHelper, BadgrTestCase):
    def setUp(self):
        super(UserRecipientIdentifierTests, self).setUp()

        self.badgr_app = BadgrApp(cors='testserver',
                                  email_confirmation_redirect='http://testserver/login/',
                                  forgot_password_redirect='http://testserver/reset-password/')
        self.badgr_app.save()

        self.first_user_email = 'first.user@newemail.test'
        self.first_user_email_secondary = 'first.user+2@newemail.test'
        self.first_user = self.setup_user(email=self.first_user_email, authenticate=True)
        CachedEmailAddress.objects.create(user=self.first_user, email=self.first_user_email_secondary, verified=True)
        response = self.client.get('/v1/user/auth-token')
        self.assertEqual(response.status_code, 200)

        self.issuer = self.setup_issuer(owner=self.first_user)
        self.badgeclass = self.setup_badgeclass(self.issuer)

    def test_two_users_can_have_same_identifier(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url)
        second_user_email = 'second.user@email.com'
        second_user = self.setup_user(email=second_user_email, authenticate=True)
        second_user.userrecipientidentifier_set.create(identifier=url)

        self.assertGreater(UserRecipientIdentifier.objects.filter(identifier=url).count(), 1)

    def test_only_one_user_can_have_verified_identifier(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url, verified=True)
        second_user_email = 'second.user@email.com'
        second_user = self.setup_user(email=second_user_email, authenticate=True)
        second_identifier = second_user.userrecipientidentifier_set.create(identifier=url)

        with self.assertRaisesRegex(ValidationError, re.compile('identifier', re.I)):
            second_identifier.verified = True
            second_identifier.save()

    def test_url_format_validation(self):
        self.first_user.userrecipientidentifier_set.create(identifier='http://example.com')
        self.first_user.userrecipientidentifier_set.create(identifier='ftp://example.com')
        self.first_user.userrecipientidentifier_set.create(identifier='https://withpath.com/12345678')
        self.first_user.userrecipientidentifier_set.create(identifier='https://withhash.com/12345678/bar.html#fooey')

        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='http')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='(541) 342-8456')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='12345678')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='email@test.com')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='customprotocol://example.com')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='http://singlepart')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(identifier='/relative/url')

    def test_phone_format_validation(self):
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='3428456')
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='5413428456')
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='15413428456')
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='+15413428456')

        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(
                type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='+1541342845612345')
        with self.assertRaisesRegex(ValidationError, 'valid'):
            self.first_user.userrecipientidentifier_set.create(
                type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier='(541) 342-8456')

    def test_verified_phone_included_in_all_recipient_identifiers(self):
        identifier = '3428456'
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier=identifier, verified=True)
        self.assertIn(identifier, self.first_user.all_recipient_identifiers)

    def test_verified_url_included_in_all_recipient_identifiers(self):
        identifier = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL, identifier=identifier, verified=True)
        self.assertIn(identifier, self.first_user.all_recipient_identifiers)

    def test_identifiers_serialized_to_correct_fields(self):
        url = 'http://example.com'
        phone = '+15413428456'
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL, identifier=url, verified=True)
        self.first_user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier=phone, verified=True)
        v1serialized = BadgeUserProfileSerializerV1(self.first_user).data
        v2serialized = BadgeUserSerializerV2(self.first_user).data['result'][0]

        self.assertIn(url, v1serialized['url'])
        self.assertIn(url, v2serialized['url'])
        self.assertIn(phone, v1serialized['telephone'])
        self.assertIn(phone, v2serialized['telephone'])

        self.assertNotIn(phone, v1serialized['url'])
        self.assertNotIn(phone, v2serialized['url'])
        self.assertNotIn(url, v1serialized['telephone'])
        self.assertNotIn(url, v2serialized['telephone'])

    def test_recipient_identity_serialized_to_correct_fields(self):
        user = self.setup_user(create_email_address=False)
        v2serialized = BadgeUserSerializerV2(user).data['result'][0]
        self.assertEqual(None, v2serialized['recipient'])
        
        url = 'http://example.com'
        phone = '+15413428456'
        user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL, identifier=url, verified=True)
        user.userrecipientidentifier_set.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE, identifier=phone, verified=True)
        v2serialized = BadgeUserSerializerV2(user).data['result'][0]
        self.assertIn(url, v2serialized['recipient']['identity'])
        self.assertIn('url', v2serialized['recipient']['type'])

        primary_email = 'primary@example.com'
        CachedEmailAddress.objects.create(user=user, email=primary_email, primary=True, verified=True)
        v2serialized = BadgeUserSerializerV2(user).data['result'][0]
        self.assertIn(primary_email, v2serialized['recipient']['identity'])
        self.assertIn('email', v2serialized['recipient']['type'])

    def test_verified_recipient_receives_assertion(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url, verified=True, type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)
        self.assertEqual(len(self.first_user.cached_badgeinstances()), 1)

    def test_unverified_recipient_receives_no_assertion(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)
        self.assertEqual(len(self.first_user.cached_badgeinstances()), 0)

    def test_verified_recipient_v1_badges_endpoint(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url, verified=True, type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)

        response = self.client.get('/v1/earner/badges')
        self.assertEqual(len(response.data), 1)

    def test_verified_recipient_v2_assertions_endpoint(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url, verified=True)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)
        response = self.client.get('/v2/backpack/assertions')
        self.assertEqual(len(response.data['result']), 1)

    def test_unverified_recipient_v1_badges_endpoint(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)

        response = self.client.get('/v1/earner/badges')
        self.assertEqual(len(response.data), 0)

    def test_unverified_recipient_v2_assertions_endpoint(self):
        url = 'http://example.com'
        self.first_user.userrecipientidentifier_set.create(identifier=url)
        self.badgeclass.issue(recipient_id=url, recipient_type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL)

        response = self.client.get('/v2/backpack/assertions')
        self.assertEqual(len(response.data['result']), 0)


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
)
class UserBadgeTests(BadgrTestCase):
    def setUp(self):
        super(UserBadgeTests, self).setUp()
        self.badgr_app = BadgrApp(cors='testserver',
                                  email_confirmation_redirect='http://testserver/login/',
                                  forgot_password_redirect='http://testserver/reset-password/')
        self.badgr_app.save()

    def create_badgeclass(self):
        with open(os.path.join(TOP_DIR, 'apps', 'issuer', 'testfiles', 'guinea_pig_testing_badge.png'), 'rb') as fh:
            issuer = Issuer.objects.create(name='Issuer of Testing')
            badgeclass = BadgeClass.objects.create(
                issuer=issuer,
                name="Badge of Testing",
                image=SimpleUploadedFile(name='test_image.png', content=fh.read(), content_type='image/png')
            )
            return badgeclass

    def test_badge_awards_transferred_on_email_verification(self):
        first_user_email = 'first+user@email.test'
        first_user = self.setup_user(email=first_user_email, authenticate=True)

        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        starting_count = len(response.data)

        badgeclass = self.create_badgeclass()
        badgeclass.issue(recipient_id='New+email@newemail.com', allow_uppercase=True, recipient_type='email')
        badgeclass.issue(recipient_id='New+Email@newemail.com', allow_uppercase=True, recipient_type='email')

        outbox_count = len(mail.outbox)

        response = self.client.post('/v1/user/emails', {
            'email': 'new+email@newemail.com',
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/v1/user/emails')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(starting_count+1, len(response.data))

        # Mark email as verified
        email = CachedEmailAddress.cached.get(email='new+email@newemail.com')
        self.assertEqual(len(mail.outbox), outbox_count+1)
        verify_url = re.search("(?P<url>/v1/[^\s]+)", mail.outbox[-1].body).group("url")
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)

        email = CachedEmailAddress.cached.get(email='new+email@newemail.com')
        self.assertTrue(email.verified)

        self.assertTrue('New+email@newemail.com' in [e.email for e in email.cached_variants()])
        self.assertTrue('New+Email@newemail.com' in [e.email for e in email.cached_variants()])


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
)
class UserProfileTests(BadgrTestCase):
    def assertUserLoggedIn(self, user_pk=None):
        self.assertIn(SESSION_KEY, self.client.session)
        if user_pk is not None:
            self.assertEqual(self.client.session[SESSION_KEY], user_pk)

    def test_user_can_change_profile(self):
        first = 'firsty'
        last = 'lastington'
        new_password = 'new-password'
        username = 'testinguser'
        original_password = 'password'
        email = 'testinguser@testing.info'

        user = BadgeUser(username=username, is_active=True, email=email)
        user.set_password(original_password)
        user.save()
        self.client.login(username=username, password=original_password)
        self.assertUserLoggedIn()

        response = self.client.put('/v1/user/profile', {
            'first_name': first,
            'last_name': last,
            'password': new_password,
            'current_password': original_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(first, response.data.get('first_name'))
        self.assertEqual(last, response.data.get('last_name'))

        self.client.logout()
        self.client.login(username=username, password=new_password)
        self.assertUserLoggedIn()
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.put('/v1/user/profile', {
            'first_name': 'Barry',
            'last_name': 'Manilow'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual('Barry', response.data.get('first_name'))

        third_password = 'superstar!'
        response = self.client.put('/v1/user/profile', {
            'password': third_password,
            'current_password': new_password
        })
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        self.client.login(username=username, password=third_password)
        self.assertUserLoggedIn()

    def test_user_can_agree_to_terms(self):
        first = 'firsty'
        last = 'lastington'
        new_password = 'new-password'
        username = 'testinguser'
        original_password = 'password'
        email = 'testinguser@testing.info'

        user = BadgeUser(username=username, is_active=True, email=email)
        user.set_password(original_password)
        user.save()
        self.client.login(username=username, password=original_password)
        self.assertUserLoggedIn()

        TermsVersion.objects.create(version=1, short_description='terms 1')

        response = self.client.put('/v1/user/profile', {
            'first_name': first,
            'last_name': last,
            'password': new_password,
            'current_password': original_password,
            'latest_terms_version': 1
        })
        self.assertEqual(response.status_code, 200)

    def test_user_update_ignores_blank_email(self):
        first = 'firsty'
        last = 'lastington'
        new_password = 'new-password'
        username = 'testinguser'
        original_password = 'password'

        user = BadgeUser(username=username, is_active=True)
        user.set_password(original_password)
        user.save()
        UserRecipientIdentifier.objects.create(
            type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL,
            identifier='http://testurl.com/123',
            verified=True,
            user=user
        )
        self.client.login(username=username, password=original_password)
        self.assertUserLoggedIn()

        TermsVersion.objects.create(version=1, short_description='terms 1')

        response = self.client.put('/v1/user/profile', {
            'first_name': first + ' Q.',
            'last_name': last,
            'email': None
        }, format='json')
        self.assertEqual(response.status_code, 200)
