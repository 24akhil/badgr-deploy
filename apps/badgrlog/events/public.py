# Created by wiggins@concentricsky.com on 8/27/15.
from .base import BaseBadgrEvent
from mainsite.utils import client_ip_from_request


class BaseBadgeAssertionEvent(BaseBadgrEvent):
    def __init__(self, badge_instance, request):
        self.badge_instance = badge_instance
        self.request = request

    def to_representation(self):
        return {
            'ipAddress': client_ip_from_request(self.request),
            'badgeInstance': self.badge_instance.json,
            'referer': self.request.META.get('HTTP_REFERER')
        }


class BadgeAssertionCheckedEvent(BaseBadgeAssertionEvent):
    pass


class RevokedBadgeAssertionCheckedEvent(BaseBadgeAssertionEvent):
    pass


class BadgeInstanceDownloadedEvent(BaseBadgeAssertionEvent):
    pass


class BadgeClassRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class BadgeClassCriteriaRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class BadgeClassImageRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class IssuerRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class IssuerBadgesRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class IssuerImageRetrievedEvent(BaseBadgeAssertionEvent):
    pass


class PathwayElementRetrievedEvent(BaseBadgrEvent):
    def __init__(self, pathway_element, request):
        self.request = request
        self.pathway_element = pathway_element

    def to_representation(self):
        return {
            'ipAddress': client_ip_from_request(self.request),
            'pathwayElement': self.pathway_element
        }
