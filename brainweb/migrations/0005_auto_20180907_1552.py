# Generated by Django 2.0.1 on 2018-09-07 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brainweb', '0004_auto_20180901_0559'),
    ]

    operations = [
        migrations.RenameField(
            model_name='individual',
            old_name='fitness_relative',
            new_name='fitness_relative_all',
        ),
        migrations.AddField(
            model_name='individual',
            name='fitness_relative_adult',
            field=models.FloatField(default=0),
        ),
    ]
