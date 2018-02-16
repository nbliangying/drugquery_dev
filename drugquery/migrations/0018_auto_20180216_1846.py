# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-02-16 18:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drugquery', '0017_auto_20180130_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='gene',
            name='num_compounds',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gene',
            name='num_dockings',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gene',
            name='num_pdbs',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gene',
            name='num_pockets',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gene',
            name='num_targets',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pdb',
            name='num_compounds',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pdb',
            name='num_dockings',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pdb',
            name='num_pockets',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pdb',
            name='num_targets',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pocket',
            name='num_compounds',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pocket',
            name='num_dockings',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='target',
            name='num_compounds',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='target',
            name='num_dockings',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='target',
            name='num_pockets',
            field=models.IntegerField(default=0),
        ),
    ]
