
from office_db.russian_regions import TRussianRegions
from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory
from common.urllib_parse_pro import urlsplit_pro
from web_site_db.web_sites import TDeclarationWebSiteList

import json
import argparse
from collections import defaultdict
import os.path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--wikidata-info", dest='wikidata_info')
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()

"""
    SELECT ?item ?itemLabel ?website ?district ?oblast
    WHERE
    {
      VALUES ?russian_district { wd:Q2198484 wd:Q634099}
      ?item wdt:P31 ?russian_district.
      ?item wdt:P856 ?website.
      ?item wdt:P131 ?district.
      ?district wdt:P131 ?oblast.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
    }

"""
class TWikidataRecords:
    def __init__(self, regions):
        self.records = None
        self.name2wikidata = defaultdict(list);
        self.regions = regions

    def read_from_file(self, filepath):
        with open(filepath) as inp:
            self.records = json.load(inp)
        for x in self.records:
            self.name2wikidata[x['itemLabel']].append(x)

    def get_region_by_name(self, name):
        if name not in self.name2wikidata:
            return None, None
        regions = set()
        for x in self.name2wikidata.get(name, []):
            url = x['oblast']
            region_wikidata_id = os.path.basename(url)
            region_id = self.regions.get_region_by_wikidata_id(region_wikidata_id)
            if region_id is None:
                continue
            entry_id = os.path.basename(x['item'])
            regions.add((entry_id, region_id))
        if len(regions) == 1:
            return list(regions)[0]
        return None, None

    def get_region_by_url(self, name, url):
        if name not in self.name2wikidata:
            return None, None
        regions = set()
        (_, netloc1, _, _, _) = urlsplit_pro(url)
        for x in self.name2wikidata.get(name, []):
            (_, netloc2, _, _, _) = urlsplit_pro(x['website'])
            if netloc1 == netloc2:
                region_wikidata_id = os.path.basename(x['oblast'])
                region_id = self.regions.get_region_by_wikidata_id(region_wikidata_id)
                if region_id is None:
                    continue
                entry_id = os.path.basename(x['item'])
                regions.add((entry_id, region_id))
        if len(regions) == 1:
            return list(regions)[0]
        return None, None


def main():
    args = parse_args()
    logger = setup_logging("calc_region_from_wd")
    regions = TRussianRegions()
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()
    wd = TWikidataRecords(regions)
    wd.read_from_file(args.wikidata_info)

    web_sites_db = TDeclarationWebSiteList(logger,
                                           TDeclarationWebSiteList.default_input_task_list_path).load_from_disk()
    office_to_urls = web_sites_db.build_office_to_main_website(take_abandoned=True)
    with open(args.input_file) as inp:
        for l in inp:
            office_id, name = l.strip().split("\t")
            office = offices.offices.get(int(office_id))
            if office is None:
                logger.debug("cannot find office_id={}, name={} no valid urls, deleted office?")
                continue

            wikidata_id, region = wd.get_region_by_name(name)
            if wikidata_id is not None:
                cause = "name"
            else:
                urls = office_to_urls.get(int(office_id), [])
                if len(urls) == 0:
                    logger.debug("office_id={}, name={} no valid urls, delete office?")
                    continue
                for url in urls:
                    wikidata_id, region = wd.get_region_by_url(name, url)
                    if wikidata_id is not None:
                        cause = "url"
                        break

            if region is None:
                logger.error(
                    "office_id={}, name={} cannot recognize region".format(office_id, name))
            else:
                logger.debug("set region {} to {} {} by {} ".format(region.name, office_id, name, cause))
                office.region_id = region.id
                office.wikidata_id = wikidata_id
    logger.info("write to {}".format(args.output_file))
    offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()