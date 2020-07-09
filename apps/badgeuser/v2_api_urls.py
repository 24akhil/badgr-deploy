# encoding: utf-8


from django.conf.urls import url

from badgeuser.api import (BadgeUserAccountConfirm, BadgeUserToken, BadgeUserForgotPassword, BadgeUserEmailConfirm,
                           BadgeUserDetail, AccessTokenList, AccessTokenDetail, LatestTermsVersionDetail,)

urlpatterns = [

    url(r'^auth/token$', BadgeUserToken.as_view(), name='v2_api_auth_token'),
    url(r'^auth/forgot-password$', BadgeUserForgotPassword.as_view(), name='v2_api_auth_forgot_password'),
    url(r'^auth/confirm-email/(?P<confirm_id>[^/]+)$', BadgeUserEmailConfirm.as_view(), name='v2_api_auth_confirm_email'),
    url(r'^auth/confirm-account/(?P<authcode>[^/]+)$', BadgeUserAccountConfirm.as_view(), name='v2_api_account_confirm'),

    url(r'^auth/tokens$', AccessTokenList.as_view(), name='v2_api_access_token_list'),
    url(r'^auth/tokens/(?P<entity_id>[^/]+)$', AccessTokenDetail.as_view(), name='v2_api_access_token_detail'),

    url(r'^users/(?P<entity_id>self)$', BadgeUserDetail.as_view(), name='v2_api_user_self'),
    url(r'^users/(?P<entity_id>[^/]+)$', BadgeUserDetail.as_view(), name='v2_api_user_detail'),

    url(r'^termsVersions/latest$', LatestTermsVersionDetail.as_view(), name='v2_latest_terms_version_detail'),
]