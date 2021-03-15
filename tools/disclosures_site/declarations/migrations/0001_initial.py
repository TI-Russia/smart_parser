# Generated by Django 3.0.5 on 2020-04-11 20:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(verbose_name='region name')),
                ('wikibase_id', models.CharField(max_length=10, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Region_Synonyms',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('synonym', models.TextField(verbose_name='region synonym')),
                ('synonym_class', models.IntegerField(null=True)),
                ('region',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.region',
                                   verbose_name='region')),
            ],
        ),
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(verbose_name='office name')),
                ('type_id', models.IntegerField(null=True)),
                ('parent_id', models.IntegerField(null=True)),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.region',
                                   verbose_name='region', null=True)),
                ('rubric_id', models.IntegerField(default=None, null=True))
            ],
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('person_name', models.CharField(max_length=64, verbose_name='person name')),
                ('declarator_person_id', models.IntegerField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Source_Document',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('sha256', models.CharField(max_length=200)),
                ('file_extension', models.CharField(max_length=16)),
                ('intersection_status', models.CharField(max_length=16)),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.office',
                                             verbose_name='office name')),
                ('max_income_year', models.IntegerField(default=None, null=True)),
                ('min_income_year', models.IntegerField(default=None, null=True)),
                ('section_count', models.IntegerField(default=0, null=True)),
                ('median_income', models.IntegerField(default=0, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Declarator_File_Reference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('declarator_documentfile_id', models.IntegerField(null=True)),
                ('declarator_document_id', models.IntegerField(null=True)),
                ('declarator_document_file_url', models.TextField(null=True)),
                ('source_document',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 to='declarations.source_document', verbose_name='source document')),
                ('web_domain', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Web_Reference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dlrobot_url', models.TextField(null=True)),
                ('crawl_epoch', models.IntegerField(null=True)),
                ('source_document',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.source_document',
                                   verbose_name='source document')),
                ('web_domain', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('person_name', models.CharField(max_length=64, verbose_name='person name')),
                ('income_year', models.IntegerField(null=True)),
                ('department', models.TextField(null=True)),
                ('position', models.TextField(null=True)),
                ('person', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='declarations.Person', verbose_name='person id')),
                ('dedupe_score', models.FloatField(blank=True, default=0.0, null=True)),
                ('source_document', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                                 to='declarations.source_document', verbose_name='source document')),
                ('surname_rank', models.IntegerField(null=True)),
                ('name_rank', models.IntegerField(null=True)),
                ('rubric_id', models.IntegerField(null=True, default=None)),
                ('gender', models.PositiveSmallIntegerField(default=None, null=True)),
            ]

        ),
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relative', models.CharField(max_length=1)),
                ('name', models.TextField()),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.Section')),
            ],
        ),
        migrations.CreateModel(
            name='RealEstate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.TextField(verbose_name='real_estate')),
                ('country', models.CharField(max_length=2)),
                ('relative', models.CharField(max_length=1)),
                ('owntype', models.CharField(max_length=1)),
                ('square', models.IntegerField(null=True)),
                ('share', models.FloatField(null=True)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.Section')),
            ],
        ),
        migrations.CreateModel(
            name='Income',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.IntegerField(null=True)),
                ('relative', models.CharField(max_length=1)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.Section')),
            ],
        ),
        migrations.CreateModel(
            name='Person_Rating',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.TextField(verbose_name='rating name')),
                ('image_file_path', models.TextField(verbose_name='file path')),
                ('rating_unit_name', models.TextField(verbose_name='rating_unit')),
            ],
        ),
        migrations.CreateModel(
            name='Person_Rating_Items',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('person_place', models.IntegerField()),
                ('rating_year', models.IntegerField()),
                ('rating_value', models.IntegerField()),
                ('competitors_number', models.IntegerField(default=0)),
                ('office',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='declarations.office')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.person')),
                ('rating',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='declarations.person_rating')),
            ],
        ),

    ]
