from django.db import migrations, models
import gzip
#from declarations.models import Office

def add_offices(apps, schema_editor):
    Office = apps.get_model('declarations', 'Office')
    Office.objects.all().delete()
    # select id, parent_id, type_id, region_id, name_ru from declarations_office into outfile "/var/lib/mysql-files/offices.txt";
    # mv /var/lib/mysql-files/offices.txt data
    # gzip data/offices.txt
    for line in gzip.open("data/offices.txt.gz"):
        items = tuple( (None if (x == "\\N") else x) for x in line.decode('utf8').strip().split("\t", 4))
        id, parent_id, type_id, region_id, name_ru = items
        name_ru = name_ru.replace("\t", " ")
        c = Office(id=int(id),
                   name=name_ru,
                   type_id=int(type_id))
        if parent_id is not None:
            c.parent_id = int(parent_id)
        if region_id is not None:
            c.region_id = int(region_id)
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

