# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-10-08 13:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bundesliga_app', '0002_auto_20181001_1038'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discount',
            name='value',
            field=models.IntegerField(),
        ),
    ]