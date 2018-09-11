# Generated by Django 2.0.1 on 2018-09-01 00:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('compiler', models.CharField(default='', max_length=100)),
                ('matemutator', models.CharField(default='', max_length=100)),
                ('code', models.TextField(default='.', max_length=10000000)),
                ('code_compiled', models.TextField(default='.', max_length=10000000)),
                ('code_size', models.IntegerField(default=0)),
                ('memory', models.TextField(default='', max_length=10000000)),
                ('memory_size', models.IntegerField(default=0)),
                ('fitness', models.FloatField(default=0)),
                ('fitness_sum', models.FloatField(default=0)),
                ('fitness_relative', models.FloatField(default=0)),
                ('fitness_evaluations', models.IntegerField(default=0)),
                ('executions', models.IntegerField(default=0)),
                ('program_steps', models.IntegerField(default=0)),
                ('memory_usage', models.IntegerField(default=0)),
                ('execution_time', models.FloatField(default=0)),
            ],
            options={
                'ordering': ['-fitness'],
            },
        ),
        migrations.CreateModel(
            name='Peer',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('lastfail', models.DateTimeField(blank=True, default=None, null=True)),
                ('host', models.CharField(default='', max_length=200)),
                ('port', models.IntegerField(default=4141)),
                ('supernode', models.BooleanField(default=False)),
                ('failcount', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Population',
            fields=[
                ('id', models.BigAutoField(db_index=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('best_individual_id', models.CharField(default='', max_length=200)),
                ('best_individual_fitness', models.FloatField(default=0)),
                ('individuals_created', models.IntegerField(default=0)),
                ('timespend', models.IntegerField(default=0)),
                ('timespend_total', models.IntegerField(default=0)),
                ('fitness_relative', models.FloatField(default=1)),
                ('fitness_evaluations', models.IntegerField(default=0)),
                ('fitness_evaluations_total', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['-best_individual_fitness'],
            },
        ),
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('name', models.CharField(default='', max_length=200, unique=True)),
                ('description', models.CharField(default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ReferenceFunction',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('name', models.CharField(default='', max_length=200, unique=True)),
                ('fitness', models.FloatField(default=0)),
                ('fitness_sum', models.FloatField(default=0)),
                ('fitness_relative', models.FloatField(default=0)),
                ('fitness_evaluations', models.IntegerField(default=0)),
                ('executions', models.IntegerField(default=0)),
                ('program_steps', models.IntegerField(default=0)),
                ('memory_usage', models.IntegerField(default=0)),
                ('execution_time', models.FloatField(default=0)),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referencefunctions', to='brainweb.Problem')),
            ],
            options={
                'ordering': ['-fitness'],
            },
        ),
        migrations.CreateModel(
            name='Species',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('name', models.CharField(default='', max_length=200, unique=True)),
                ('usePriorKnowledge', models.BooleanField(default=False)),
                ('useP2P', models.BooleanField(default=False)),
                ('max_populations', models.IntegerField(default=10)),
                ('max_populationsize', models.IntegerField(default=100)),
                ('min_populationsize', models.IntegerField(default=50)),
                ('max_code_length', models.IntegerField(default=20)),
                ('min_code_length', models.IntegerField(default=20)),
                ('max_fitness_evaluations', models.IntegerField(default=100)),
                ('min_fitness_evaluations', models.IntegerField(default=10)),
                ('max_memory', models.IntegerField(default=20)),
                ('max_permanent_memory', models.IntegerField(default=20)),
                ('max_steps', models.IntegerField(default=-1)),
                ('problems', models.ManyToManyField(db_index=True, related_name='species', to='brainweb.Problem')),
            ],
            options={
                'ordering': ['-updated'],
            },
        ),
        migrations.AddField(
            model_name='population',
            name='species',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='populations', to='brainweb.Species'),
        ),
        migrations.AddField(
            model_name='individual',
            name='population',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='individuals', to='brainweb.Population'),
        ),
    ]
