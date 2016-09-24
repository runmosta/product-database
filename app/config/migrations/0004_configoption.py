# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-19 19:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0003_auto_20160907_2057'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=256, unique=True)),
                ('value', models.CharField(blank=True, max_length=256, null=True)),
            ],
        ),
    ]
