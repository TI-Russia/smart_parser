from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory
from common.urllib_parse_pro import urlsplit_pro
from office_db.declaration_office_website import TDeclarationWebSite
from office_db.russian_regions import TRussianRegions, TRegion
import json
import argparse
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wd-url-info", dest='wikidata_info')
    parser.add_argument("--wd-region-head-info", dest='wd_region_head_info')
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()

#1. go to https://query.wikidata.org, 2.input the following query
"""
    SELECT ?item ?itemLabel ?website
    WHERE
    {
      ?item wdt:P17 wd:Q159.
      ?item wdt:P856 ?website.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
    }

"""
#3. save as org_with_urls.json (without detail) 4. pass org_with_urls.json to --wd-url-info


#главы регионов (файл region_heads.json)
# SELECT ?item ?itemLabel ?website
#     WHERE
#     {
#       ?item wdt:P279 wd:Q1540324.
#       SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
#     }

def get_web_domain(url):
    web_domain = urlsplit_pro(url).hostname
    if web_domain.startswith("www."):
        web_domain = web_domain[4:]
    return web_domain


class TWikidataUrlRecords:
    def __init__(self):
        self.records = None
        self.hostnames = defaultdict(list);

    def read_from_file(self, filepath):
        with open(filepath) as inp:
            self.records = json.load(inp)
        for x in self.records:
            web_domain = get_web_domain(x['website'])
            self.hostnames[web_domain].append(x)


class TWikidataRegionHeads:
    def __init__(self):
        self.records = None
        self.titles = defaultdict(list)


    def read_from_file(self, filepath):
        with open(filepath) as inp:
            self.records = json.load(inp)
        for x in self.records:
            self.titles[x['itemLabel'].lower()].append(x)


class TWikiDataMatcher:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging("wd_by_url")
        self.regions = TRussianRegions()
        self.offices = TOfficeTableInMemory(use_office_types=False)
        self.offices.read_from_local_file()
        self.disclosures_hostnames = defaultdict(set)
        self.disclosures_office_names = defaultdict(set)
        self.build_office_indices()
        self.wd_urls = TWikidataUrlRecords()
        self.wd_urls.read_from_file(self.args.wikidata_info)
        self.wd_region_heads = TWikidataRegionHeads()
        self.wd_region_heads.read_from_file(self.args.wd_region_head_info)

    def build_office_indices(self):
        office: TOfficeInMemory
        self.disclosures_hostnames = defaultdict(set)
        self.disclosures_office_names.clear()
        for office in self.offices.offices.values():
            self.disclosures_office_names[office.name.lower()].add(office)
            site_info: TDeclarationWebSite
            for site_info in office.office_web_sites:
                if site_info.can_communicate():
                    self.disclosures_hostnames[get_web_domain(site_info.url)].add(office)

    def find_wikidata_entry(self, hostname, wd_infos) -> TOfficeInMemory:
        if len(wd_infos) == 1:
            found = self.disclosures_hostnames.get(hostname, list())
            if len(found) == 0:
                self.logger.debug("cannot find {} in disclosures".format(hostname))
            elif len(found) > 1:
                self.logger.debug("hostname  {} is ambiguous".format(hostname))
            else:
                return list(found)[0], wd_infos[0]
        else:
            found = self.disclosures_hostnames.get(hostname, list())
            if len(found) == 0:
                self.logger.debug("{} is ambiguous in wikidata, but it also useless since it cannot be found in disclosures".format(hostname))
                return None
            elif len(found) > 1:
                self.logger.debug("hostname  {} is ambiguous in wikidata and in disclosures".format(hostname))
            else:
                office: TOfficeInMemory
                office = list(found)[0]
                for w in wd_infos:
                    if w['itemLabel'].lower() == office.name.lower():
                        return office, w
                for w in wd_infos:
                    if w['itemLabel'].lower().startswith(office.name.lower()):
                        return office, w
                for w in wd_infos:
                    if office.name.lower().startswith(w['itemLabel'].lower()):
                        return office, w

                return None

    def set_wikidata_id(self, cause, office, wikidata_id, wikidata_label):
        if wikidata_id.startswith('http://www.wikidata.org/entity/'):
            wikidata_id = wikidata_id[len('http://www.wikidata.org/entity/'):]

        if self.regions.get_region_by_wikidata_id(wikidata_id) is not None:
            self.logger.debug(
                "skip region wikidata set cause={} office.name = {} to wikidata = https://www.wikidata.org/wiki/{} , wikidata.title={}".format(
                    cause, office.name, wikidata_id, wikidata_label))
            return

        if office.wikidata_id is None:
            office.wikidata_id = wikidata_id
            self.logger.debug(
                "set cause={} office.name = {} to wikidata = https://www.wikidata.org/wiki/{} , wikidata.title={}".format(
                    cause, office.name, wikidata_id, wikidata_label))
        elif office.wikidata_id != wikidata_id:
            self.logger.error(
                "office https://disclosures.ru/office/{} {} has  wikidata_id=https://www.wikidata.org/wiki/{}, "
                "but the input file has https://www.wikidata.org/wiki/{}, skip it".format(
                    office.office_id, office.name, office.wikidata_id, wikidata_id))

    def process_offices_urls(self):
        for hostname, wd_infos in self.wd_urls.hostnames.items():
            r = self.find_wikidata_entry(hostname, wd_infos)
            if r is not None:
                office, wd_info = r
                self.set_wikidata_id(hostname, office, wd_info["item"], wd_info["itemLabel"])

    def process_offices_region_heads(self):
        for name, wd_infos in self.wd_region_heads.titles.items():
            found = self.disclosures_office_names.get(name)
            if found is None:
                self.logger.error("region head name {} cannot be found in disclosures".format(name))
            elif len(found) > 1:
                self.logger.error("region head name {} is ambiguous in disclosures".format(name))
            else:
                office = list(found)[0]
                wd_info = wd_infos[0]
                self.set_wikidata_id(name, office, wd_info["item"], wd_info["itemLabel"])


def main():
    # offices = TOfficeTableInMemory(use_office_types=False)
    # offices.read_from_local_file()
    # regions = TRussianRegions()
    # r: TRegion
    # ids = set( r.wikidata_id for r in regions.regions)
    #
    # o: TOfficeInMemory
    # for o in offices.offices.values():
    #     if o.wikidata_id in ids:
    #         print ("office.id = {}, office.name={}, wikidata=https://www.wikidata.org/wiki/{}".format(
    #             o.office_id, o.name, o.wikidata_id))
    # return

    args = parse_args()
    m = TWikiDataMatcher(args)
    m.process_offices_urls()
    m.process_offices_region_heads()
    m.logger.info("write to {}".format(args.output_file))
    m.offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()