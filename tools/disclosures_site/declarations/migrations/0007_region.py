from django.db import migrations, models
from declarations.models import SynonymClass
import gzip


#echo  "select * from declarations_region" | mysql -D declarator -u declarator -pdeclarator | gzip -c > data/regions.txt.gz
def add_regions(apps, schema_editor):
    clear_regions(apps, schema_editor)
    cnt = 0
    header = ""
    Region = apps.get_model('declarations', 'Region')
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')

    for line in gzip.open("data/regions.txt.gz"):
        line = line.decode('utf8').strip()
        cnt += 1
        if cnt == 1:
            assert line.find('federal_district_id') != -1
            header = list(line.split("\t"))
        else:
            items = list(line.split("\t"))
            r = Region()
            synonyms = dict()
            assert len(header) == len(items)
            for k, v in zip(header, items):
                if k == 'id':
                    r.id = int(v)
                elif k == "name":
                    r.name = v
                    synonyms[v] = SynonymClass.Russian
                elif k == "short_name" or k == "extra_short_name":
                    if v not in synonyms:
                        synonyms[v] = SynonymClass.RussianShort
                elif k == "name_en":
                    if v not in synonyms:
                        synonyms[v] = SynonymClass.English
                elif k == "short_name_en":
                    if v not in synonyms:
                        synonyms[v] = SynonymClass.EnglishShort
            r.save()
            for k, v in synonyms.items():
                if k is None or k == "":
                    continue
                k = k.strip('*')
                s = RegionSynonyms()
                s.region = r
                s.synonym = k.lower()
                s.synonym_class = v
                s.save()



def clear_regions(apps, schema_editor):
    Region = apps.get_model('declarations', 'Region')
    Region.objects.all().delete()
    RegionSynonyms = apps.get_model('declarations', 'Region_Synonyms')
    RegionSynonyms.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('declarations', '0006_init_regions'),
    ]
    operations = [
        migrations.RunPython(add_regions, clear_regions)
    ]

