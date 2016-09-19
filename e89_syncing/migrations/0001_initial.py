# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        (settings.SYNC_USER_MODEL.split(".")[0], "0001_initial")
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.ForeignKey(to=settings.SYNC_USER_MODEL)),
                ('timestamp', models.DateTimeField()),
                ('identifier', models.CharField(max_length=100))
            ],
            bases=(models.Model,),
        )
    ]
