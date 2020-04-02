from django.db import migrations, models
import gzip

def add_countries(apps, schema_editor):
    Country = apps.get_model('declarations', 'Country')
    Country.objects.all().delete()
    for line in open("data/countries.txt", "r", encoding="utf8"):
        fields = line.strip().split("\t")
        name_ru, name_en, alpha2, alpha3, code = map ((lambda x: "" if (x=="\\N") else x),  fields)
        c = Country(name=name_ru, name_ru=name_ru, name_en=name_en, alpha2=alpha2, alpha3=alpha3, code=code)
        c.save()


def clear_countries(apps, schema_editor):
    Country = apps.get_model('declarations', 'Country')
    Country.objects.all().delete()


def add_relatives(apps, schema_editor):
    Relative = apps.get_model('declarations', 'Relative')
    Relative.objects.all().delete()
    relatives = [
        ("cупруг(а)", "spouse"),
        ("ребенок", "child")
    ]
    for r,e in relatives:
        c = Relative(name=r, name_ru=r, name_en=e)
        c.save()


def clear_relatives(apps, schema_editor):
    Relative = apps.get_model('declarations', 'Relative')
    Relative.objects.all().delete()


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
        migrations.RunPython(add_countries, clear_countries),
        migrations.RunPython(add_relatives, clear_relatives),
        migrations.RunPython(add_offices, clear_offices)
    ]

