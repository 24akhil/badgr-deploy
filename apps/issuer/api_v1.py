# encoding: utf-8


from apispec_drf.decorators import apispec_list_operation, apispec_operation
from django.contrib.auth import get_user_model
from rest_framework import status, authentication
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

import badgrlog
from badgeuser.models import CachedEmailAddress
from entity.api import VersionedObjectMixin
from issuer.models import Issuer, IssuerStaff
from issuer.permissions import IsOwnerOrStaff, BadgrOAuthTokenHasEntityScope
from issuer.serializers_v1 import BadgeClassSerializerV1, IssuerRoleActionSerializerV1, IssuerStaffSerializerV1
from issuer.utils import get_badgeclass_by_identifier
from mainsite.permissions import AuthenticatedWithVerifiedIdentifier, IsServerAdmin
from mainsite.utils import throttleable

logger = badgrlog.BadgrLogger()


class AbstractIssuerAPIEndpoint(APIView):
    authentication_classes = (
        authentication.TokenAuthentication,
        authentication.SessionAuthentication,
        authentication.BasicAuthentication,
    )
    permission_classes = (AuthenticatedWithVerifiedIdentifier,)

    def get_object(self, slug, queryset=None):
        """ Ensure user has permissions on Issuer """

        queryset = queryset if queryset is not None else self.queryset
        try:
            obj = queryset.get(entity_id=slug)
        except self.model.DoesNotExist:
            return None

        try:
            self.check_object_permissions(self.request, obj)
        except PermissionDenied:
            return None
        else:
            return obj

    def get_list(self, slug=None, queryset=None, related=None):
        """ Ensure user has permissions on Issuer, and return badgeclass queryset if so. """
        queryset = queryset if queryset is not None else self.queryset

        obj = queryset
        if slug is not None:
            obj = queryset.filter(slug=slug)
        if related is not None:
            obj = queryset.select_related(related)

        if not obj.exists():
            return self.model.objects.none()

        try:
            self.check_object_permissions(self.request, obj[0])
        except PermissionDenied:
            return self.model.objects.none()
        else:
            return obj


class IssuerStaffList(VersionedObjectMixin, APIView):
    """ View or modify an issuer's staff members and privileges """
    role = 'staff'
    queryset = Issuer.objects.all()
    model = Issuer
    permission_classes = [
        IsServerAdmin |
        (AuthenticatedWithVerifiedIdentifier & IsOwnerOrStaff) |
        BadgrOAuthTokenHasEntityScope
    ]
    valid_scopes = {
        "get": ["rw:issuerOwner:*"],
        "post": ["rw:issuerOwner:*"],
        "@apispec_scopes": {}
    }

    @apispec_list_operation('IssuerStaff',
        tags=['Issuers'],
        summary="Get a list of users associated with a role on an Issuer"
    )
    def get(self, request, **kwargs):
        current_issuer = self.get_object(request, **kwargs)
        if not self.has_object_permissions(request, current_issuer):
            return Response(
                "Issuer %s not found. Authenticated user must have owner, editor or staff rights on the issuer.".format(
                    kwargs.get('slug')
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = IssuerStaffSerializerV1(
            IssuerStaff.objects.filter(issuer=current_issuer),
            many=True
        )

        if len(serializer.data) == 0:
            return Response([], status=status.HTTP_200_OK)
        return Response(serializer.data)

    @apispec_operation(
        tags=['Issuers'],
        summary="Add or remove a user from a role on an issuer. Limited to Owner users only"
    )
    @throttleable
    def post(self, request, **kwargs):
        """
        ---
        parameters:
            - name: slug
              type: string
              paramType: path
              description: The slug of the issuer whose roles to modify.
              required: true
            - name: action
              type: string
              paramType: form
              description: The action to perform on the user. Must be one of 'add', 'modify', or 'remove'.
              required: true
            - name: username
              type: string
              paramType: form
              description: The username of the user to add or remove from this role.
              required: false
            - name: email
              type: string
              paramType: form
              description: A verified email address of the user to add or remove from this role.
              required: false
            - name: role
              type: string
              paramType: form
              description: Role to set user as. One of 'owner', 'editor', or 'staff'
              defaultValue: staff
              required: false
        """
        # validate POST data
        serializer = IssuerRoleActionSerializerV1(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        current_issuer = self.get_object(request, **kwargs)

        user_id = None
        try:
            if serializer.validated_data.get('username'):
                user_id = serializer.validated_data.get('username')
                user_to_modify = get_user_model().objects.get(username=user_id)
            else:
                user_id = serializer.validated_data.get('email')
                user_to_modify = CachedEmailAddress.objects.get(
                    email=user_id, verified=True).user
        except (get_user_model().DoesNotExist, CachedEmailAddress.DoesNotExist,):
            error_text = "User not found. Email must correspond to an existing user."
            if user_id is None:
                error_text = 'User not found. Neither email address or username was provided.'
            return Response(
                error_text, status=status.HTTP_404_NOT_FOUND
            )

        if user_to_modify == request.user:
            return Response("Cannot modify your own permissions on an issuer profile",
                            status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data.get('action')
        if action == 'add':
            role = serializer.validated_data.get('role')
            staff_instance, created = IssuerStaff.objects.get_or_create(
                user=user_to_modify,
                issuer=current_issuer,
                defaults={
                    'role': role
                }
            )

            if created is False:
                raise ValidationError("Could not add user to staff list. User already in staff list.")

        elif action == 'modify':
            role = serializer.validated_data.get('role')
            try:
                staff_instance = IssuerStaff.objects.get(
                    user=user_to_modify,
                    issuer=current_issuer
                )
                staff_instance.role = role
                staff_instance.save(update_fields=('role',))
            except IssuerStaff.DoesNotExist:
                raise ValidationError("Cannot modify staff record. Matching staff record does not exist.")

        elif action == 'remove':
            IssuerStaff.objects.filter(user=user_to_modify, issuer=current_issuer).delete()
            current_issuer.publish(publish_staff=False)
            user_to_modify.publish()
            return Response(
                "User %s has been removed from %s staff." % (user_to_modify.username, current_issuer.name),
                status=status.HTTP_200_OK)

        # update cached issuers and badgeclasses for user
        user_to_modify.save()

        return Response(IssuerStaffSerializerV1(staff_instance).data)


class FindBadgeClassDetail(APIView):
    """
    GET a specific BadgeClass by searching by identifier
    """
    permission_classes = (AuthenticatedWithVerifiedIdentifier,)

    @apispec_operation(
        summary="Get a specific BadgeClass by searching by identifier",
        tags=['BadgeClasses'],
        parameters=[
            {
                "in": "query",
                "name": "identifier",
                'required': True,
                "description": "The identifier of the badge possible values: JSONld identifier, BadgeClass.id, or BadgeClass.slug"
            }
        ]
    )
    def get(self, request, **kwargs):
        identifier = request.query_params.get('identifier')
        badge = get_badgeclass_by_identifier(identifier)
        if badge is None:
            raise NotFound("No BadgeClass found by identifier: {}".format(identifier))

        serializer = BadgeClassSerializerV1(badge)
        return Response(serializer.data)

