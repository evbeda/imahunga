# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-10-29 13:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bundesliga_app', '0008_auto_20181025_1007'),
    ]

    operations = [
        migrations.CreateModel(
            name='MemberDiscountCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_number', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='StatusDiscountCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.RemoveField(
            model_name='discountcode',
            name='eb_event_id',
        ),
        migrations.RemoveField(
            model_name='discountcode',
            name='member_number',
        ),
        migrations.AddField(
            model_name='memberdiscountcode',
            name='discount_code',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bundesliga_app.DiscountCode'),
        ),
        migrations.AddField(
            model_name='memberdiscountcode',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bundesliga_app.StatusDiscountCode'),
        ),
    ]
