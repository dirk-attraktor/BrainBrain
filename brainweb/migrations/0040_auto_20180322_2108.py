# Generated by Django 2.0.1 on 2018-03-22 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brainweb', '0039_lock'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='useP2P',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='problem',
            name='usePriorKnowledge',
            field=models.BooleanField(default=False),
        ),
    ]