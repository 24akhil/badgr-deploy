from rest_framework import permissions


class IsSocialAccountOwner(permissions.BasePermission):
    """
    Only grant access to owner of SocialAccount.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user