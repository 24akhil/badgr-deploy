# -*- coding: utf-8 -*-


from django.db import models, migrations


def noop(apps, schema_editor):
    pass


def migrate_localbadgeinstance_to_use_issuer(apps, schema_editor):
    LocalBadgeInstance = apps.get_model('composition', 'LocalBadgeInstance')
    BadgeClass = apps.get_model('issuer', 'BadgeClass')
    for local_badge_instance in LocalBadgeInstance.objects.all():
        try:
            source_url = getattr(local_badge_instance.local_badgeclass, 'identifier', None)

            badgeclass = BadgeClass.objects.get(source='legacy_local_badgeclass',
                                                source_url=source_url)
            local_badge_instance.issuer_badgeclass = badgeclass
            local_badge_instance.save()
        except BadgeClass.DoesNotExist:
            pass

    pass


class Migration(migrations.Migration):

    dependencies = [
        ('composition', '0012_localbadgeinstance_badgeclass'),
        ('issuer', '0017_auto_20170227_1334'),
    ]

    operations = [
        migrations.RunPython(migrate_localbadgeinstance_to_use_issuer, reverse_code=noop),
    ]
