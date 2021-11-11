from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory

from django.db import migrations


def add_offices(apps, schema_editor):
    clear_offices(apps, schema_editor)
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()
    Office = apps.get_model('declarations', 'Office')
    office: TOfficeInMemory
    for office in offices.offices.values():
        c = Office(id=office.office_id,
                   name=office.name,
                   type_id=office.type_id,
                   parent_id=office.parent_id,
                   region_id=office.region_id,
                   rubric_id=office.rubric_id
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

