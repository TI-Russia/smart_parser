from django.db import migrations
import gzip
import json
from declarations.rubrics import build_one_rubric
import declarations.models as models


#echo  "select *  from declarations_region" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator  | gzip -c > data/regions.txt.gz
def add_offices(apps, schema_editor):
    clear_offices(apps, schema_editor)
    with gzip.open("data/offices.txt.gz") as inp:
        offices = json.load(inp)
    office_hierarchy = models.TOfficeHierarchy(use_office_types=False, init_from_json=offices)
    Office = apps.get_model('declarations', 'Office')
    for office in offices:
        c = Office(id=office['id'],
                   name=office['name_ru'],
                   type_id=office['type_id'],
                   parent_id=office['parent_id'],
                   region_id=office['region_id'],
                   rubric_id=build_one_rubric(None, office_hierarchy, office['id'])
                   )
        print (c.rubric_id)
        c.save()


def clear_offices(apps, schema_editor):
    Office = apps.get_model('declarations', 'Office')
    Office.objects.all().delete()



class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('declarations', '0002_region'),
    ]
    operations = [
        migrations.RunPython(add_offices, clear_offices)
    ]

