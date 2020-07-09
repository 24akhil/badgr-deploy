# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainsite', '0004_auto_20170120_1724'),
    ]

    operations = [
        migrations.AddField(
            model_name='badgrapp',
            name='ui_login_redirect',
            field=models.URLField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='badgrapp',
            name='ui_signup_success_redirect',
            field=models.URLField(null=True),
            preserve_default=True,
        ),
    ]
