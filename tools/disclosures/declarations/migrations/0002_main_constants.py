from django.db import migrations, models
import gzip

def add_offices(apps, schema_editor):
    Office = apps.get_model('declarations', 'Office')
    Office.objects.all().delete()
    for line in gzip.open("data/offices.txt.gz"):
        id, name_ru = line.decode('utf8').strip().split("\t", 1)
        name_ru = name_ru.replace("\t", " ")
        c = Office(id=int(id), name=name_ru, name_ru=name_ru)
        c.save()

def clear_offices(apps, schema_editor):
    Office = apps.get_model('declarations', 'Office')
    Office.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('declarations', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(add_offices, clear_offices)
    ]

