# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-26 15:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bundesliga_app', '0003_auto_20180926_1218'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='discount',
            name='membertype',
        ),
        migrations.DeleteModel(
            name='MemberType',
        ),
    ]