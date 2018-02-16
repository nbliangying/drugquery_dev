# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-14 14:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drugquery', '0014_auto_20170908_1533'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='email',
            field=models.EmailField(default='#', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='upload',
            name='email',
            field=models.EmailField(default='#', max_length=254),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='docking',
            name='docking_file',
            field=models.FileField(upload_to='dockings'),
        ),
    ]