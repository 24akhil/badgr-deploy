# -*- coding: utf-8 -*-


from django.db import models, migrations

from entity.db.migrations import PopulateEntityIdsMigration


class Migration(migrations.Migration):

    dependencies = [
        ('badgeuser', '0007_auto_20170427_0957'),
    ]

    operations = [
        PopulateEntityIdsMigration('badgeuser', 'BadgeUser'),
    ]
