from django.db import migrations, models
from declarations.models import SynonymClass
import gzip
import json

#echo  "select *  from declarations_region" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator  | gzip -c > data/regions.txt.gz
def add_regions(apps, schema_editor):
    clear_regions(apps, schema_editor)
    Region = apps.get_model('declarations', 'Region')
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')
    with gzip.open("data/regions.txt.gz") as inp:
        regions = json.load(inp)
    for r in regions:
        rec = Region(
            id=r['id'],
            name=r['name']
        )
        rec.save()
        synonyms = {
            r['name']: SynonymClass.Russian,
            r["short_name"]: SynonymClass.RussianShort,
            r["extra_short_name"]: SynonymClass.RussianShort,
            r["name_en"]: SynonymClass.English,
            r["extra_short_name"]: SynonymClass.EnglishShort
        }

        for k, v in synonyms.items():
            if k == "":
                continue
            k = k.strip('*')
            s = RegionSynonyms()
            s.region = rec
            s.synonym = k
            s.synonym_class = v
            s.save()


def clear_regions(apps, schema_editor):
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')
    RegionSynonyms.objects.all().delete()
    Region = apps.get_model('declarations', 'Region')
    Region.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('declarations', '0006_init_regions'),
    ]
    operations = [
        migrations.RunPython(add_regions, clear_regions)
    ]

