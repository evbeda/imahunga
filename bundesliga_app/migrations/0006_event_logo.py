# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-27 15:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bundesliga_app', '0005_event_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='logo',
            field=models.CharField(default='', max_length=500),
        ),
    ]