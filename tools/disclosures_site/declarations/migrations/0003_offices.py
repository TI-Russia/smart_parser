from django.db import migrations
import json

import declarations.offices_in_memory
from declarations.rubrics import build_office_rubric
import declarations.models as models
import os


#echo  "select *  from declarations_office" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator data/offices.txt
#echo  "select * from declarator.declarations_office  where id not in (select id from disclosures_db.declarations_office)" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator > offices.txt
def add_offices(apps, schema_editor):
    clear_offices(apps, schema_editor)
    filepath = os.path.join(os.path.dirname(__file__), "../../data/offices.txt")
    with open(filepath) as inp:
        offices = json.load(inp)
    office_hierarchy = declarations.offices_in_memory.TOfficeTableInMemory(use_office_types=False)
    office_hierarchy.read_from_json(offices)
    Office = apps.get_model('declarations', 'Office')
    for office in offices:
        c = Office(id=office['id'],
                   name=office['name'],
                   type_id=office['type_id'],
                   parent_id=office['parent_id'],
                   region_id=office['region_id'],
                   rubric_id=build_office_rubric(None, office_hierarchy, office['id'])
                   )
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

