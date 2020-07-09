# encoding: utf-8


import os.path
from urllib.parse import quote_plus

import os
import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.files.images import get_image_dimensions
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import Application

from badgeuser.models import CachedEmailAddress, UserRecipientIdentifier
from issuer.models import Issuer, BadgeClass, IssuerStaff
from mainsite.models import ApplicationInfo, AccessTokenProxy
from mainsite.tests import SetupOAuth2ApplicationHelper
from mainsite.tests.base import BadgrTestCase, SetupIssuerHelper


@override_settings(TOKEN_BACKOFF_MAXIMUM_SECONDS=0)  # disable token backoff
class IssuerTests(SetupOAuth2ApplicationHelper, SetupIssuerHelper, BadgrTestCase):
    example_issuer_props = {
        'name': 'Awesome Issuer',
        'description': 'An issuer of awe-inspiring credentials',
        'url': 'http://example.com',
        'email': 'contact@example.org'
    }

    def setUp(self):
        cache.clear()
        super(IssuerTests, self).setUp()

    def test_cant_create_issuer_if_unauthenticated(self):
        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertIn(response.status_code, (401, 403))

    def test_v2_issuers_badgeclasses_can_paginate(self):
        NUM_BADGE_CLASSES = 5
        PAGINATE = 2

        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)
        test_badgeclasses = list(self.setup_badgeclasses(issuer=test_issuer, how_many=NUM_BADGE_CLASSES))

        response = self.client.get('/v2/issuers/{slug}/badgeclasses?num={num}'.format(
            slug=test_issuer.entity_id,
            num=PAGINATE)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(test_badgeclasses), NUM_BADGE_CLASSES)
        self.assertEqual(len(response.data.get('result')), PAGINATE)

    def test_create_issuer_if_authenticated(self):
        test_user = self.setup_user(authenticate=True)
        issuer_email = CachedEmailAddress.objects.create(
            user=test_user, email=self.example_issuer_props['email'], verified=True)

        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 201)

        # assert that name, description, url, etc are set properly in response badge object
        badge_object = response.data.get('json')
        self.assertEqual(badge_object['url'], self.example_issuer_props['url'])
        self.assertEqual(badge_object['name'], self.example_issuer_props['name'])
        self.assertEqual(badge_object['description'], self.example_issuer_props['description'])
        self.assertEqual(badge_object['email'], self.example_issuer_props['email'])
        self.assertIsNotNone(badge_object.get('id'))
        self.assertIsNotNone(badge_object.get('@context'))

        # assert that the issuer was published to and fetched from the cache
        with self.assertNumQueries(0):
            slug = response.data.get('slug')
            response = self.client.get('/v1/issuer/issuers/{}'.format(slug))
            self.assertEqual(response.status_code, 200)

    def test_cant_create_issuer_if_authenticated_with_unconfirmed_email(self):
        self.setup_user(authenticate=True, verified=False)

        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 403)

    def _create_issuer_with_image_and_test_resizing(self, image_path, desired_width=400, desired_height=400):
        test_user = self.setup_user(authenticate=True)
        issuer_email = CachedEmailAddress.objects.create(
            user=test_user, email=self.example_issuer_props['email'], verified=True)

        with open(image_path, 'rb') as badge_image:
            issuer_fields_with_image = self.example_issuer_props.copy()
            issuer_fields_with_image['image'] = badge_image

            response = self.client.post('/v1/issuer/issuers', issuer_fields_with_image, format='multipart')
            self.assertEqual(response.status_code, 201)

            self.assertIn('slug', response.data)
            issuer_slug = response.data.get('slug')
            new_issuer = Issuer.objects.get(entity_id=issuer_slug)

            image_width, image_height = get_image_dimensions(new_issuer.image.file)
            self.assertEqual(image_width, desired_width)
            self.assertEqual(image_height, desired_height)

    def test_create_issuer_image_500x300_resizes_to_400x400(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '500x300.png')
        self._create_issuer_with_image_and_test_resizing(image_path)

    def test_create_issuer_image_450x450_resizes_to_400x400(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '450x450.png')
        self._create_issuer_with_image_and_test_resizing(image_path)

    def test_create_issuer_image_300x300_stays_300x300(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '300x300.png')
        self._create_issuer_with_image_and_test_resizing(image_path, 300, 300)

    def test_issuer_update_resizes_image(self):
        desired_width = desired_height = 400

        test_user = self.setup_user(authenticate=True)
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '500x300.png')
        image = open(image_path, 'rb')
        encoded = 'data:image/png;base64,' + base64.b64encode(image.read()).decode()

        issuer_email = CachedEmailAddress.objects.create(
                user=test_user, email=self.example_issuer_props['email'], verified=True)

        issuer_fields_with_image = self.example_issuer_props.copy()
        issuer_fields_with_image['image'] = encoded

        response = self.client.post('/v1/issuer/issuers', issuer_fields_with_image)
        self.assertEqual(response.status_code, 201)
        response_slug = response.data.get('slug')
        new_issuer = Issuer.objects.get(entity_id=response_slug)

        image_width, image_height = get_image_dimensions(new_issuer.image.file)
        self.assertEqual(image_width, desired_width)
        self.assertEqual(image_height, desired_height)

        # Update the issuer with the original 500x300 image
        issuer_fields_with_image['image'] = encoded

        update_response = self.client.put('/v1/issuer/issuers/{}'.format(response_slug), issuer_fields_with_image)
        self.assertEqual(update_response.status_code, 200)
        update_response_slug = update_response.data.get('slug')
        updated_issuer = Issuer.objects.get(entity_id=update_response_slug)

        update_image_width, update_image_height = get_image_dimensions(updated_issuer.image.file)
        self.assertEqual(update_image_width, desired_width)
        self.assertEqual(update_image_height, desired_height)


    def test_can_update_issuer_if_authenticated(self):
        test_user = self.setup_user(authenticate=True)

        original_issuer_props = {
            'name': 'Test Issuer Name',
            'description': 'Test issuer description',
            'url': 'http://example.com/1',
            'email': 'example1@example.org'
        }

        issuer_email_1 = CachedEmailAddress.objects.create(
            user=test_user, email=original_issuer_props['email'], verified=True)

        response = self.client.post('/v1/issuer/issuers', original_issuer_props)
        response_slug = response.data.get('slug')

        updated_issuer_props = {
            'name': 'Test Issuer Name 2',
            'description': 'Test issuer description 2',
            'url': 'http://example.com/2',
            'email': 'example2@example.org'
        }

        issuer_email_2 = CachedEmailAddress.objects.create(
            user=test_user, email=updated_issuer_props['email'], verified=True)

        response = self.client.put('/v1/issuer/issuers/{}'.format(response_slug), updated_issuer_props)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data['url'], updated_issuer_props['url'])
        self.assertEqual(response.data['name'], updated_issuer_props['name'])
        self.assertEqual(response.data['description'], updated_issuer_props['description'])
        self.assertEqual(response.data['email'], updated_issuer_props['email'])

        # test that subsequent GETs include the updated data
        response = self.client.get('/v2/issuers')
        response_issuers = response.data['result']
        self.assertEqual(len(response_issuers), 1)
        self.assertEqual(response_issuers[0]['url'], updated_issuer_props['url'])
        self.assertEqual(response_issuers[0]['name'], updated_issuer_props['name'])
        self.assertEqual(response_issuers[0]['description'], updated_issuer_props['description'])
        self.assertEqual(response_issuers[0]['email'], updated_issuer_props['email'])

    def test_get_empty_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.get('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  # Assert that there is just a single owner

    def test_add_user_to_issuer_editors_set_by_email(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        other_user = self.setup_user(authenticate=False)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email,
            'role': 'editor'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # Assert that there is now one editor

    def test_add_user_to_issuer_editors_set_by_email_with_issueradmin_scope(self):
        test_user = self.setup_user(authenticate=True, token_scope='rw:serverAdmin')
        test_owner = self.setup_user(authenticate=False)
        issuer = self.setup_issuer(owner=test_owner)
        other_user = self.setup_user(authenticate=False)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email,
            'role': 'editor'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # Assert that there is now one editor

    def test_cannot_add_user_by_unverified_email(self):
        test_user = self.setup_user(authenticate=True)
        self.client.force_authenticate(user=test_user)

        user_to_update = self.setup_user()
        new_email = CachedEmailAddress.objects.create(
            user=user_to_update, verified=False, email='newemailsonew@example.com')

        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'email': new_email.email, 'role': 'editor'}
        )

        self.assertEqual(post_response.status_code, 404)

    def test_add_user_to_issuer_editors_set_too_many_methods(self):
        """
        Enter a username or email. Both are not allowed.
        """
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'email': 'test3@example.com',
            'username': 'test3',
            'role': 'editor'
        })
        self.assertEqual(response.status_code, 400)

    def test_add_user_to_issuer_editors_set_missing_identifier(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'role': 'editor'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, 'User not found. Neither email address or username was provided.')

    def test_bad_action_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'DO THE HOKEY POKEY',
            'username': 'test2',
            'role': 'editor'
        })
        self.assertEqual(response.status_code, 400)

    def test_add_nonexistent_user_to_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        erroneous_username = 'wronguser'
        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'username': erroneous_username,
            'role': 'editor'
        })
        self.assertContains(response, "User not found.".format(erroneous_username), status_code=404)

    def test_add_user_to_nonexistent_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        erroneous_issuer_slug = 'wrongissuer'
        response = self.client.post(
            '/v1/issuer/issuers/{slug}/staff'.format(slug=erroneous_issuer_slug),
            {'action': 'add', 'username': 'test2', 'role': 'editor'}
        )
        self.assertEqual(response.status_code, 404)

    def test_add_remove_user_with_issuer_staff_set(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        other_user = self.setup_user(authenticate=False)

        self.assertEqual(len(test_issuer.staff.all()), 1)

        first_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email
        })
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 2)

        second_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'remove',
            'email': other_user.primary_email
        })
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 1)

    def test_modify_staff_user_role(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)
        self.assertEqual(test_issuer.staff.count(), 1)

        other_user = self.setup_user(authenticate=False)

        first_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email
        })
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 2)
        self.assertEqual(test_issuer.editors.count(), 1)
        self.assertEqual(test_issuer.staff.count(), 2)

        second_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'modify',
            'email': other_user.primary_email,
            'role': 'editor'
        })
        self.assertEqual(second_response.status_code, 200)
        staff = test_issuer.staff.all()
        self.assertEqual(test_issuer.editors.count(), 2)

    def test_cannot_modify_or_remove_self(self):
        """
        The authenticated issuer owner cannot modify their own role or remove themself from the list.
        """
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)
        self.client.force_authenticate(user=test_user)
        post_response = self.client.post(
            '/v1/issuer/issuers/{}/staff'.format(test_issuer.entity_id),
            {'action': 'remove', 'email': test_user.email}
        )

        self.assertEqual(post_response.status_code, 400)

        post_response = self.client.post(
            '/v1/issuer/issuers/{}/staff'.format(test_issuer.entity_id),
            {'action': 'modify', 'email': test_user.email, 'role': 'staff'}
        )

        self.assertEqual(post_response.status_code, 400)

    def test_delete_issuer_successfully(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 204)

    def test_editor_cannot_delete_issuer(self):
        test_user = self.setup_user(authenticate=True)
        test_owner = self.setup_user(authenticate=False)
        test_issuer = self.setup_issuer(owner=test_owner)
        IssuerStaff.objects.create(user=test_user, issuer=test_issuer, role=IssuerStaff.ROLE_EDITOR)

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 404)

    def test_delete_issuer_with_unissued_badgeclass_successfully(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        test_badgeclass = BadgeClass(name="Deletable Badge", issuer=test_issuer)
        test_badgeclass.save()

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 204)

    def test_cant_delete_issuer_with_issued_badge(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        test_badgeclass = self.setup_badgeclass(issuer=test_issuer)
        test_badgeclass.issue(recipient_id='new-bage-recipient@email.test')

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 400)

    def test_cant_create_issuer_with_unverified_email_v1(self):
        test_user = self.setup_user(authenticate=True)
        new_issuer_props = {
            'name': 'Test Issuer Name',
            'description': 'Test issuer description',
            'url': 'http://example.com/1',
            'email': 'example1@example.org'
        }

        response = self.client.post('/v1/issuer/issuers', new_issuer_props)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data[0],
            'Issuer email must be one of your verified addresses. Add this email to your profile and try again.')

    def test_cant_create_issuer_with_unverified_email_v2(self):
        test_user = self.setup_user(authenticate=True)
        new_issuer_props = {
            'name': 'Test Issuer Name',
            'description': 'Test issuer description',
            'url': 'http://example.com/1',
            'email': 'example1@example.org'
        }

        response = self.client.post('/v2/issuers', new_issuer_props)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['validationErrors'][0],
            'Issuer email must be one of your verified addresses. Add this email to your profile and try again.')

    def test_trusted_user_can_create_issuer_with_unverified_email(self):
        test_user = self.setup_user(authenticate=True)
        application = Application.objects.create(user=test_user)
        app_info = ApplicationInfo.objects.create(application=application, trust_email_verification=True)

        new_issuer_props = {
            'name': 'Test Issuer Name',
            'description': 'Test issuer description',
            'url': 'http://example.com/1',
            'email': 'an+unknown+email@badgr.test'
        }

        response = self.client.post('/v2/issuers', new_issuer_props)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/v1/issuer/issuers', new_issuer_props)
        self.assertEqual(response.status_code, 201)

    def test_issuer_staff_serialization(self):
        test_user = self.setup_user(authenticate=True)

        # issuer_email = CachedEmailAddress.objects.create(
        #     user=test_user, email=self.example_issuer_props['email'], verified=True)

        email_staff= self.setup_user()

        url_staff = self.setup_user(email="", create_email_address=False)
        url_for_staff = UserRecipientIdentifier.objects.create(type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL,
                                                               identifier='http://example.com',
                                                               user=url_staff, verified=True)
        url_for_staff2 = UserRecipientIdentifier.objects.create(type=UserRecipientIdentifier.IDENTIFIER_TYPE_URL,
                                                               identifier='http://example2.com',
                                                               user=url_staff, verified=False)

        phone_staff = self.setup_user(email="", create_email_address=False)
        phone_for_staff = UserRecipientIdentifier.objects.create(type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE,
                                                                 identifier='5555555555',
                                                                 user=phone_staff, verified=True)
        phone_for_staff2 = UserRecipientIdentifier.objects.create(type=UserRecipientIdentifier.IDENTIFIER_TYPE_TELEPHONE,
                                                                 identifier='5555555556',
                                                                 user=phone_staff, verified=False)

        issuer = self.setup_issuer(owner=test_user)

        #add url user as staff
        response1 = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'username': url_staff.username,
            'role': 'staff'
        })
        self.assertEqual(response1.status_code, 200)

        #add phone user as editor
        response2 = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'username': phone_staff.username,
            'role': 'editor'
        })
        self.assertEqual(response2.status_code, 200)

        #get issuer object and check staff serialization
        response = self.client.get('/v2/issuers')
        response_issuers = response.data['result']
        self.assertEqual(len(response_issuers), 1)
        our_issuer = response_issuers[0]
        self.assertEqual(len(our_issuer['staff']), 3)
        for staff_user in our_issuer['staff']:
            if (staff_user['role'] == IssuerStaff.ROLE_OWNER):
                #check emails
                self.assertEqual(len(staff_user['userProfile']['url']), 0)
                self.assertEqual(len(staff_user['userProfile']['telephone']), 0)
                self.assertEqual(len(staff_user['userProfile']['emails']), 1)
            elif (staff_user['role'] == IssuerStaff.ROLE_EDITOR):
                #check phone
                self.assertEqual(len(staff_user['userProfile']['url']), 0)
                self.assertEqual(len(staff_user['userProfile']['telephone']), 1)
                self.assertEqual(staff_user['userProfile']['telephone'][0], phone_for_staff.identifier)
                self.assertFalse(phone_for_staff2.identifier in staff_user['userProfile']['telephone'])
                self.assertEqual(len(staff_user['userProfile']['emails']), 0)
            else:
                self.assertEqual(len(staff_user['userProfile']['url']), 1)
                self.assertEqual(staff_user['userProfile']['url'][0], url_for_staff.identifier)
                self.assertFalse(url_for_staff2.identifier in staff_user['userProfile']['url'])
                self.assertEqual(len(staff_user['userProfile']['telephone']), 0)
                self.assertEqual(len(staff_user['userProfile']['emails']), 0)

    def test_can_edit_staff_with_oauth(self):
        issuer_owner = self.setup_user(authenticate=False)
        test_issuer = self.setup_issuer(owner=issuer_owner)

        user = self.setup_user(email='lilstudent@example.com')
        client_app_user = self.setup_user(email='clientApp@example.com', token_scope='rw:issuerOwner:*')
        app = Application.objects.create(
            client_id='clientApp-authcode', client_secret='testsecret', authorization_grant_type='authorization-code',
            user=client_app_user)
        ApplicationInfo.objects.create(application=app, allowed_scopes='rw:issuerOwner*')
        t = AccessTokenProxy.objects.create(
            user=client_app_user, scope='rw:issuerOwner:' + test_issuer.entity_id,
            expires=timezone.now() + timezone.timedelta(hours=1),
            token='123', application=app
        )
        self.client.credentials(HTTP_AUTHORIZATION="Bearer 123")
        badgr_user_email = 'user@email.test'
        badgr_user = self.setup_user(email=badgr_user_email, authenticate=False)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'add',
            'email': badgr_user_email,
            'role': 'staff'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(IssuerStaff.objects.filter(user=badgr_user)), 1)

        # Verify token cannot be used to modify some other issuer
        other_issuer = self.setup_issuer(owner=issuer_owner)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=other_issuer.entity_id), {
            'action': 'add',
            'email': badgr_user_email,
            'role': 'staff'
        })
        self.assertEqual(response.status_code, 404)


class IssuersChangedApplicationTests(SetupIssuerHelper, BadgrTestCase):
    def test_application_can_get_changed_issuers(self):
        issuer_user = self.setup_user(authenticate=True, verified=True, token_scope='rw:serverAdmin')
        test_issuer = self.setup_issuer(owner=issuer_user)
        test_issuer2 = self.setup_issuer(owner=issuer_user)
        test_issuer3 = self.setup_issuer(owner=issuer_user)

        other_user = self.setup_user(authenticate=False, verified=True)
        other_issuer = self.setup_issuer(owner=other_user)
        other_issuer2 = self.setup_issuer(owner=other_user)
        other_issuer3 = self.setup_issuer(owner=other_user)

        response = self.client.get('/v2/issuers/changed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['result']), 3)
        timestamp = response.data['timestamp']

        response = self.client.get('/v2/issuers/changed?since={}'.format(quote_plus(timestamp)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['result']), 0)

        test_issuer.name = 'Issuer updated'
        test_issuer.save()

        response = self.client.get('/v2/issuers/changed?since={}'.format(quote_plus(timestamp)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['result']), 1)


class ApprovedIssuersOnlyTests(SetupIssuerHelper, BadgrTestCase):
    example_issuer_props = {
        'name': 'Awesome Issuer',
        'description': 'An issuer of awe-inspiring credentials',
        'url': 'http://example.com',
        'email': 'contact@example.org'
    }

    @override_settings(BADGR_APPROVED_ISSUERS_ONLY=True)
    def test_unapproved_user_cannot_create_issuer(self):
        test_user = self.setup_user(authenticate=True)
        issuer_email = CachedEmailAddress.objects.create(
            user=test_user, email=self.example_issuer_props['email'], verified=True)

        response = self.client.post('/v2/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 404)

    @override_settings(BADGR_APPROVED_ISSUERS_ONLY=True)
    def test_approved_user_can_create_issuer(self):
        test_user = self.setup_user(authenticate=True)
        issuer_email = CachedEmailAddress.objects.create(
            user=test_user, email=self.example_issuer_props['email'], verified=True)

        permission = Permission.objects.get_by_natural_key('add_issuer', 'issuer', 'issuer')
        group = Group.objects.create(name='test issuers')
        group.permissions.add(permission)
        group.user_set.add(test_user)

        response = self.client.post('/v2/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 201)
