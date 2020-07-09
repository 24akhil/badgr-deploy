import oauth2_provider
import rest_framework
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions
import rules

from issuer.models import IssuerStaff

SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']


@rules.predicate
def is_owner(user, issuer):
    for staff_record in issuer.cached_issuerstaff():
        if staff_record.user_id == user.id and staff_record.role == IssuerStaff.ROLE_OWNER:
            return True
    return False


@rules.predicate
def is_editor(user, issuer):
    for staff_record in issuer.cached_issuerstaff():
        if staff_record.user_id == user.id and staff_record.role in (IssuerStaff.ROLE_OWNER, IssuerStaff.ROLE_EDITOR):
            return True
    return False


@rules.predicate
def is_staff(user, issuer):
    for staff_record in issuer.cached_issuerstaff():
        if staff_record.user_id == user.id:
            return True
    return False


is_on_staff = is_owner | is_staff
is_staff_editor = is_owner | is_editor

rules.add_perm('issuer.is_owner', is_owner)
rules.add_perm('issuer.is_editor', is_staff_editor)
rules.add_perm('issuer.is_staff', is_on_staff)


@rules.predicate
def is_badgeclass_owner(user, badgeclass):
    return any(staff.role == IssuerStaff.ROLE_OWNER for staff in badgeclass.cached_issuer.cached_issuerstaff() if staff.user_id == user.id)


@rules.predicate
def is_badgeclass_editor(user, badgeclass):
    return any(staff.role in [IssuerStaff.ROLE_EDITOR, IssuerStaff.ROLE_OWNER] for staff in badgeclass.cached_issuer.cached_issuerstaff() if staff.user_id == user.id)


@rules.predicate
def is_badgeclass_staff(user, badgeclass):
    return any(staff.user_id == user.id for staff in badgeclass.cached_issuer.cached_issuerstaff())

can_issue_badgeclass = is_badgeclass_owner | is_badgeclass_staff
can_edit_badgeclass = is_badgeclass_owner | is_badgeclass_editor

rules.add_perm('issuer.can_issue_badge', can_issue_badgeclass)
rules.add_perm('issuer.can_edit_badgeclass', can_edit_badgeclass)


class MayIssueBadgeClass(permissions.BasePermission):
    """
    Allows those who have been given permission to issue badges on an Issuer to create
    IssuerAssertions from its IssuerBadgeClasses
    ---
    model: BadgeClass
    """

    def has_object_permission(self, request, view, badgeclass):
        return request.user.has_perm('issuer.can_issue_badge', badgeclass)


class MayEditBadgeClass(permissions.BasePermission):
    """
    Request.user is authorized to perform safe operations on a BadgeClass
    if they are on its issuer's staff. They may perform unsafe operations
    on a BadgeClass if they are among its issuers' editors.
    ---
    model: BadgeClass
    """

    def has_object_permission(self, request, view, badgeclass):
        if request.method in SAFE_METHODS:
            return request.user.has_perm('issuer.can_issue_badge', badgeclass)
        else:
            return request.user.has_perm('issuer.can_edit_badgeclass', badgeclass)


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Ensures request user is owner for unsafe operations, or at least
    staff for safe operations.
    """
    def has_object_permission(self, request, view, issuer):
        if request.method in SAFE_METHODS:
            return request.user.has_perm('issuer.is_staff', issuer)
        else:
            return request.user.has_perm('issuer.is_owner', issuer)


class IsEditor(permissions.BasePermission):
    """
    Request.user is authorized to perform safe operations if they are staff or
    perform unsafe operations if they are owner or editor of an issuer.
    ---
    model: Issuer
    """

    def has_object_permission(self, request, view, issuer):
        if request.method in SAFE_METHODS:
            return request.user.has_perm('issuer.is_staff', issuer)
        else:
            return request.user.has_perm('issuer.is_editor', issuer)


class IsEditorButOwnerForDelete(permissions.BasePermission):
    """
    Request.user is authorized to perform safe operations if they are staff or
    perform unsafe operations if they are owner or editor of an issuer.
    ---
    model: Issuer
    """

    def has_object_permission(self, request, view, issuer):
        if request.method in SAFE_METHODS:
            return request.user.has_perm('issuer.is_staff', issuer)
        elif request.method == 'DELETE':
            return request.user.has_perm('issuer.is_owner', issuer)
        else:
            return request.user.has_perm('issuer.is_editor', issuer)


class IsStaff(permissions.BasePermission):
    """
    Request user is authorized to perform operations if they are owner or on staff
    of an Issuer.
    ---
    model: Issuer
    """
    def has_object_permission(self, request, view, issuer):
        return request.user.has_perm('issuer.is_staff', issuer)


class ApprovedIssuersOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == 'POST' and getattr(settings, 'BADGR_APPROVED_ISSUERS_ONLY', False):
            return request.user.has_perm('issuer.add_issuer')
        return True

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, None)


class IsIssuerEditor(IsEditor):
    """
    Used as a proxy permission for objects that have a .cached_issuer property and want to delegate permissions to issuer
    """
    def has_object_permission(self, request, view, recipient_group):
        return super(IsIssuerEditor, self).has_object_permission(request, view, recipient_group.cached_issuer)


class IsIssuerStaff(IsStaff):
    """
    Used as a proxy permission for objects that have a .cached_issuer property and want to delegate permissions to issuer
    """
    def has_object_permission(self, request, view, recipient_group):
        return super(IsIssuerStaff, self).has_object_permission(request, view, recipient_group.cached_issuer)


class AuditedModelOwner(permissions.BasePermission):
    """
    Request user matches .created_by
    ---
    model: BaseAuditedModel
    """
    def has_object_permission(self, request, view, obj):
        created_by_id = getattr(obj, 'created_by_id', None)
        return created_by_id and request.user.id == created_by_id


class VerifiedEmailMatchesRecipientIdentifier(permissions.BasePermission):
    """
    One of request user's verified emails matches obj.recipient_identifier.
    For badges imported by this user, they can delete the badge.
    ---
    model: BadgeInstance
    """
    def has_object_permission(self, request, view, obj):
        recipient_identifier = getattr(obj, 'recipient_identifier', None)
        if getattr(obj, 'pending', False):
            return recipient_identifier and recipient_identifier in request.user.all_recipient_identifiers
        return recipient_identifier and recipient_identifier in request.user.all_verified_recipient_identifiers


class AuthorizationIsBadgrOAuthToken(permissions.BasePermission):
    message = 'Invalid token'

    def has_permission(self, request, view):
        return isinstance(request.auth, oauth2_provider.models.AccessToken)


class BadgrOAuthTokenHasScope(permissions.BasePermission):
    def has_permission(self, request, view):
        valid_scopes = self.valid_scopes_for_view(view, method=request.method)
        token = request.auth

        if not token:
            if '*' in valid_scopes:
                return True

            # fallback scopes for authenticated users
            if request.user and request.user.is_authenticated:
                default_auth_scopes = set(['rw:profile', 'rw:issuer', 'rw:backpack'])
                if len(set(valid_scopes) & default_auth_scopes) > 0:
                    return True

            return False

        # Do not apply scope if using a non-oauth tokens
        if not isinstance(token, oauth2_provider.models.AccessToken):
            return True

        # default behavior of token.is_valid(valid_scopes) requires ALL of valid_scopes on the token
        # we want to check if ANY of valid_scopes are present in the token
        matching_scopes = set(valid_scopes) & set(token.scope.split())
        return not token.is_expired() and len(matching_scopes) > 0


    @classmethod
    def valid_scopes_for_view(cls, view, method=None):
        valid_scopes = getattr(view, "valid_scopes", [])
        if isinstance(valid_scopes, dict) and method is not None:
            for m in (method, method.lower(), method.upper()):
                if m in valid_scopes:
                    return valid_scopes[m]
            return []

        return valid_scopes


class BadgrOAuthTokenHasEntityScope(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        token = request.auth

        # This fails for authentication methods other than oauth2 token auth. Compose view permissions correctly.
        if not isinstance(token, oauth2_provider.models.AccessToken):
            return False

        # badgeclass/assertion objects defer to the issuer for permissions
        if hasattr(obj, 'cached_issuer'):
            entity_id = obj.cached_issuer.entity_id
        else:
            entity_id = obj.entity_id

        valid_scopes = self._get_valid_scopes(request, view)
        valid_scopes = [s for s in valid_scopes if '*' in s]
        valid_scopes = set([self._resolve_wildcard(scope, entity_id) for scope in valid_scopes])
        token_scopes = set(token.scope.split())

        return not token.is_expired() and len(valid_scopes.intersection(token_scopes)) > 0

    def _resolve_wildcard(self, scope, entity_id):
        if scope.endswith(':*'):
            base_scope, _ = scope.rsplit(':*', 1)
            return ':'.join([base_scope, entity_id])
        else:
            return scope

    def _get_valid_scopes(self, request, view):
        return getattr(view, "valid_scopes")
