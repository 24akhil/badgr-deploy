# encoding: utf-8


import dateutil
import requests
from celery.utils.log import get_task_logger
from django.conf import settings
from requests import ConnectionError

import badgrlog
from issuer.helpers import BadgeCheckHelper
from issuer.managers import resolve_source_url_referencing_local_object
from issuer.models import BadgeClass, BadgeInstance, Issuer
from issuer.utils import CURRENT_OBI_VERSION
from mainsite.celery import app
from mainsite.utils import OriginSetting

logger = get_task_logger(__name__)
badgrLogger = badgrlog.BadgrLogger()

background_task_queue_name = getattr(settings, 'BACKGROUND_TASK_QUEUE_NAME', 'default')
badgerank_task_queue_name = getattr(settings, 'BADGERANK_TASK_QUEUE_NAME', 'default')


@app.task(bind=True, queue=badgerank_task_queue_name, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=10)
def notify_badgerank_of_badgeclass(self, badgeclass_pk):
    badgerank_enabled = getattr(settings, 'BADGERANK_NOTIFY_ENABLED', True)
    if not badgerank_enabled:
        return {
            'success': True,
            'message': "skipping since BADGERANK_NOTIFY_ENABLED=False"
        }

    try:
        badgeclass = BadgeClass.cached.get(pk=badgeclass_pk)
    except BadgeClass.DoesNotExist:
        return {
            'success': False,
            'error': "Unknown badgeclass pk={}".format(badgeclass_pk)
        }

    badgerank_notify_url = getattr(settings, 'BADGERANK_NOTIFY_URL', 'https://api.badgerank.org/v1/badgeclass/submit')
    response = requests.post(badgerank_notify_url, json=dict(url=badgeclass.public_url))
    if response.status_code != 200:
        return {
            'success': False,
            'status_code': response.status_code,
            'response': response.content
        }
    return {
        'success': True
    }


@app.task(bind=True, queue=background_task_queue_name)
def rebake_all_assertions(self, obi_version=CURRENT_OBI_VERSION, limit=None, offset=0, replay=False):
    queryset = BadgeInstance.objects.filter(source_url__isnull=True).order_by("pk")
    if limit:
        queryset = queryset[offset:offset+limit]
    else:
        queryset = queryset[offset:]
    assertions = queryset.only("entity_id")

    count = 0
    for assertion in assertions:
        rebake_assertion_image.delay(assertion_entity_id=assertion.entity_id, obi_version=obi_version)
        count += 1

    if limit and replay and count >= limit:
        rebake_all_assertions.delay(obi_version=obi_version, limit=limit, offset=offset+limit, replay=True)

    return {
        'success': True,
        'count': count,
        'limit': limit,
        'offset': offset,
        'message': "Enqueued {} assertions for rebaking".format(count)
    }


@app.task(bind=True, queue=background_task_queue_name)
def rebake_assertion_image(self, assertion_entity_id=None, obi_version=CURRENT_OBI_VERSION):

    try:
        assertion = BadgeInstance.cached.get(entity_id=assertion_entity_id)
    except BadgeInstance.DoesNotExist as e:
        return {
            'success': False,
            'error': "Unknown assertion entity_id={}".format(assertion_entity_id)
        }

    if assertion.source_url:
        return {
            'success': False,
            'error': "Skipping imported assertion={}  source_url={}".format(assertion_entity_id, assertion.source_url)
        }

    assertion.rebake(obi_version=obi_version)

    return {
        'success': True
    }


@app.task(bind=True, queue=background_task_queue_name)
def update_issuedon_all_assertions(self, start=None, end=None):
    start_date = None
    end_date = None

    # only get assertions that were imported into backpack
    queryset = BadgeInstance.objects.filter(source_url__isnull=False)

    try:
        if start:
            start_date = dateutil.parser.parse(start)
            queryset = queryset.filter(created_at__gte=start_date)

        if end:
            end_date = dateutil.parser.parse(end)
            queryset = queryset.filter(created_at__lte=end_date)
    except ValueError:
        return {
            'success': False,
            'start': start,
            'end': end,
            'message': "Invalid date"
        }

    count = 0
    for assertion in queryset:
        update_issuedon_imported_assertion.delay(assertion.entity_id)
        count += 1

    return {
        'success': True,
        'start_date': start_date,
        'end_date': end_date,
        'totalCount': count,
    }


@app.task(bind=True, queue=background_task_queue_name)
def update_issuedon_imported_assertion(self, assertion_entityid):

    try:
        assertion = BadgeInstance.objects.get(entity_id=assertion_entityid)
    except BadgeInstance.DoesNotExist:
        return {
            'success': False,
            'assertion': assertion_entityid,
            'message': "No such assertion."
        }

    if not assertion.source_url:
        return {
            'success': False,
            'assertion': assertion_entityid,
            'message': "Not an imported assertion."
        }

    assertion_obo = BadgeCheckHelper.get_assertion_obo(assertion)
    if not assertion_obo:
        return {
            'success': False,
            'assertion': assertion_entityid,
            'message': "Unable to fetch assertion with source_url={}".format(assertion.source_url)
        }

    original_issuedOn_date = dateutil.parser.parse(assertion_obo['issuedOn'])
    updated = False

    if original_issuedOn_date != assertion.issued_on:
        assertion.issued_on = original_issuedOn_date
        assertion.save()
        updated = True

    return {
        'success': True,
        'assertion': assertion.entity_id,
        'source_url': assertion.source_url,
        'updated': updated
    }


@app.task(bind=True, queue=background_task_queue_name)
def remove_backpack_duplicates(self, limit=None, offset=0, replay=False, report_only=False):

    queryset = Issuer.objects.filter(source_url__isnull=False).order_by("pk")
    if limit:
        queryset = queryset[offset:offset+limit]
    else:
        queryset = queryset[offset:]

    imported_issuers = queryset.only("entity_id", "source_url")

    count = 0
    for issuer in imported_issuers:
        if resolve_source_url_referencing_local_object(issuer.source_url):
            remove_backpack_duplicate_issuer.delay(issuer_entity_id=issuer.entity_id, report_only=report_only)
            count += 1

    if limit and replay and count >= limit:
        remove_backpack_duplicates.delay(limit=limit, offset=offset+limit, replay=True, report_only=report_only)

    return {
        'success': True,
        'count': count,
        'limit': limit,
        'offset': offset,
        'report_only': report_only,
        'message': "Enqueued {} duplicate issuers for removal".format(count)
    }


@app.task(bind=True, queue=background_task_queue_name)
def remove_backpack_duplicate_issuer(self, issuer_entity_id=None, report_only=False):
    try:
        issuer = Issuer.objects.get(entity_id=issuer_entity_id)
    except Issuer.DoesNotExist:
        return {
            'success': False,
            'message': "No such issuer",
            'issuer_entity_id': issuer_entity_id
        }

    if not resolve_source_url_referencing_local_object(issuer.source_url):
        return {
            'success': False,
            'message': "Not a duplicate issuer",
            'issuer_entity_id': issuer_entity_id
        }

    assertions = issuer.badgeinstance_set.all()
    badgeclasses = issuer.badgeclasses.all()

    # ensure this issuer doesn't own any non-duplicate objects
    for badgeclass in badgeclasses:
        if not resolve_source_url_referencing_local_object(badgeclass.source_url):
            return {
                'success': False,
                'message': "A non-duplicate badgeclass was found owned by this issuer.",
                'issuer_entity_id': issuer_entity_id,
                'badgeclass_entity_id': badgeclass.entity_id
            }
    for assertion in assertions:
        if not resolve_source_url_referencing_local_object(assertion.source_url):
            return {
                'success': False,
                'message': "A non-duplicate assertion was found owned by this issuer.",
                'issuer_entity_id': issuer_entity_id,
                'assertion_entity_id': assertion.entity_id
            }

    assertion_count = 0
    badgeclass_count = 0
    if not report_only:
        # purge assertions, then badgeclasses, then the issuer

        for assertion in assertions:
            assertion.delete()
            assertion_count += 1

        for badgeclass in badgeclasses:
            badgeclass.delete()
            badgeclass_count += 1

        issuer.delete()

    return {
        'success': True,
        'message': "Duplicate Issuer Report" if report_only else "Issuer removed.",
        'issuer_entity_id': issuer_entity_id,
        'badgeclass_count': badgeclass_count,
        'assertion_count': assertion_count,
    }
