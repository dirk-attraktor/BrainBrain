# Generated by Django 2.0.1 on 2018-10-03 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brainweb', '0008_auto_20180915_0700'),
    ]

    operations = [
        migrations.AddField(
            model_name='population',
            name='solved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='species',
            name='solved',
            field=models.BooleanField(default=False),
        ),
    ]
