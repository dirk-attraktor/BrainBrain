# Generated by Django 2.0.1 on 2018-09-12 20:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('brainweb', '0006_species_individuals_created'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='species',
            name='usePriorKnowledge',
        ),
    ]