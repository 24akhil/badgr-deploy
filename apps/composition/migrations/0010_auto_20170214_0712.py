# -*- coding: utf-8 -*-


from django.db import models, migrations
from mainsite.utils import fetch_remote_file_to_storage

import json


def noop(apps, schema_editor):
    pass


def import_localissuers_to_issuer(apps, schema_editor):
    LocalIssuer = apps.get_model('composition', 'LocalIssuer')
    Issuer = apps.get_model('issuer', 'Issuer')
    for local_issuer in LocalIssuer.objects.all():

        remote_image_url = local_issuer.json.get('image', None)
        if local_issuer.image:
            image = local_issuer.image
        elif remote_image_url and local_issuer.image_preview_status is None:
            try:
                status_code, image = fetch_remote_file_to_storage(remote_image_url, upload_to=local_issuer.image.field.upload_to)
            except IOError:
                image = None
        else:
            image = None

        new_issuer, created = Issuer.objects.get_or_create(
            source='legacy_local_issuer',
            source_url=local_issuer.identifier,
            defaults={
                'created_by': local_issuer.created_by,
                'name': local_issuer.name,
                'image': image,
                'original_json': json.dumps(local_issuer.json),
                'url': local_issuer.json.get('url', None),
                'email': local_issuer.json.get('email', None),
                'description': local_issuer.json.get('description', None),
            }
        )
        new_issuer.created_at = local_issuer.created_at  # Avoid auto-now behavior
        new_issuer.save()


def import_localbadgeclass_to_issuer(apps, schema_editor):
    LocalBadgeClass = apps.get_model('composition', 'LocalBadgeClass')
    Issuer = apps.get_model('issuer', 'Issuer')
    BadgeClass = apps.get_model('issuer', 'BadgeClass')
    for local_badgeclass in LocalBadgeClass.objects.all():
        issuer = Issuer.objects.get(source='legacy_local_issuer', source_url=local_badgeclass.issuer.identifier)

        remote_image_url = local_badgeclass.json.get('image', None)
        if local_badgeclass.image:
            image = local_badgeclass.image
        elif remote_image_url and local_badgeclass.image_preview_status is None:
            try:
                status_code, image = fetch_remote_file_to_storage(remote_image_url, upload_to=local_badgeclass.image.field.upload_to)
            except IOError:
                image = None
        else:
            image = None

        new_badgeclass, created = BadgeClass.objects.get_or_create(
            source='legacy_local_badgeclass',
            source_url=local_badgeclass.identifier,
            defaults={
                'created_by': local_badgeclass.created_by,
                'name': local_badgeclass.name,
                'image': image,
                'criteria_text': local_badgeclass.criteria_text,
                'issuer': issuer,
                'original_json': json.dumps(local_badgeclass.json),
                'criteria_url': local_badgeclass.json.get('criteria', None),
                'description': local_badgeclass.json.get('description', None),
            }
        )
        new_badgeclass.created_at = new_badgeclass.created_at  # Avoid auto-now behavior
        new_badgeclass.save()


class Migration(migrations.Migration):

    dependencies = [
        ('composition', '0009_auto_20161007_1358'),
        ('issuer', '0019_auto_20170413_1136')
    ]

    operations = [
        migrations.RunPython(import_localissuers_to_issuer, reverse_code=noop),
        migrations.RunPython(import_localbadgeclass_to_issuer, reverse_code=noop),
    ]
