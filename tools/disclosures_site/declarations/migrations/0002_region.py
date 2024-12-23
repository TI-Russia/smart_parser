from django.db import migrations
from declarations.models import SynonymClass
from office_db.russian_regions import TRussianRegions


#echo  "select *  from declarations_region" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator  | gzip -c > data/regions.txt.gz
def add_regions(apps, schema_editor):
    clear_regions(apps, schema_editor)
    Region = apps.get_model('declarations', 'Region')
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')
    regions = TRussianRegions()
    for r in regions.regions:
        #if r.id == 0:
        #    continue  # skip Russian Federation

        rec = Region(
            id=r.id,
            name=r.name
        )
        rec.save()

        synonyms = {
            r.short_name: SynonymClass.RussianShort,
            r.extra_short_name: SynonymClass.RussianShort,
            r.short_name_en: SynonymClass.EnglishShort,
            r.name_en: SynonymClass.English,
            r.name: SynonymClass.Russian, # it  should be the last line in this dict, since r['name'] can be equal to r["short_name"]
        }

        for k, v in synonyms.items():
            if k != "":
                RegionSynonyms(region=rec, synonym=k.strip('*'), synonym_class=v).save()


def clear_regions(apps, schema_editor):
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')
    RegionSynonyms.objects.all().delete()
    Region = apps.get_model('declarations', 'Region')
    Region.objects.all().delete()


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('declarations', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(add_regions, clear_regions)
    ]

