# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-26 15:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bundesliga_app', '0002_auto_20180926_1156'),
    ]

    operations = [
        migrations.RenameField(
            model_name='discount',
            old_name='discount_name',
            new_name='name',
        ),
        migrations.RenameField(
            model_name='discount',
            old_name='discount_value',
            new_name='value',
        ),
        migrations.RenameField(
            model_name='discount',
            old_name='discount_value_type',
            new_name='value_type',
        ),
    ]