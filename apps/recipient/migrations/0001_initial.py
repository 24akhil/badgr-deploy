# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('issuer', '0007_auto_20151117_1555'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecipientGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_active', models.BooleanField(default=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=254)),
                ('description', models.TextField(null=True, blank=True)),
                ('created_by', models.ForeignKey(related_name='recipientgroup_created', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('issuer', models.ForeignKey(to='issuer.Issuer')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RecipientGroupMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('membership_name', models.CharField(max_length=254)),
                ('recipient_group', models.ForeignKey(to='recipient.RecipientGroup')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RecipientProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('recipient_identifier', models.EmailField(max_length=1024)),
                ('public', models.BooleanField(default=False)),
                ('display_name', models.CharField(max_length=254)),
                ('badge_user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='recipientgroupmembership',
            name='recipient_profile',
            field=models.ForeignKey(to='recipient.RecipientProfile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='recipientgroup',
            name='members',
            field=models.ManyToManyField(to='recipient.RecipientProfile', through='recipient.RecipientGroupMembership'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='recipientgroup',
            name='updated_by',
            field=models.ForeignKey(related_name='recipientgroup_updated', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
