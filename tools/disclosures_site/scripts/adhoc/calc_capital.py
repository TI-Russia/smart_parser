import json

from common.russian_regions import TRussianRegions
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", dest='input_file')
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()

"""
SELECT ?item ?itemLabel ?website ?capitalLabel
WHERE
{
  ?federal_subject wdt:P279 wd:Q43263 .
  ?item wdt:P31 ?federal_subject.
  ?item wdt:P856 ?website.
  ?item wdt:P36 ?capital.

  SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
  
}

"""

def main():
    with open("/home/sokirko/smart_parser/tools/disclosures_site/tmp/set_region/region.prod.txt") as inp:
        regions = json.load(inp)
    for r in regions:
        forms = REGIONS_ALL_FORMS.get(str(r['id']), {})
        for k in forms.keys():
            r[k] = forms[k]
    with open("/home/sokirko/smart_parser/tools/disclosures_site/tmp/set_region/regions.json") as inp:
        old_regions = TRussianRegions()
        regions_from_wikidata = json.load(inp)
        for o in regions_from_wikidata:

            region = old_regions.get_region_in_nominative(o['itemLabel'])
            if region is None:
                assert region is not None

            for x in regions:
                if x['id'] == region.id:
                    x['capital'] = o['capitalLabel']
                    x['wikidata_id'] = o['item'].split('/')[-1]

    with open("/home/sokirko/smart_parser/tools/disclosures_site/tmp/set_region/region.prod.txt.out", "w") as outp:
        json.dump(regions, outp, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    main()