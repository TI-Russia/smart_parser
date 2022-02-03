from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory
from common.urllib_parse_pro import urlsplit_pro
from office_db.declaration_office_website import TDeclarationWebSite

import json
import argparse
from collections import defaultdict
import os.path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wikidata-info", dest='wikidata_info')
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
#3. save as json (without detail) 4. pass query.json to --wikidata-info

def get_web_domain(url):
    web_domain = urlsplit_pro(url).hostname
    if web_domain.startswith("www."):
        web_domain = web_domain[4:]
    return web_domain


class TWikidataRecords:
    def __init__(self):
        self.records = None
        self.hostnames = defaultdict(list);

    def read_from_file(self, filepath):
        with open(filepath) as inp:
            self.records = json.load(inp)
        for x in self.records:
            web_domain = get_web_domain(x['website'])
            self.hostnames[web_domain].append(x)

class TWikiDataMatcher:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging("wd_by_url")
        self.offices = TOfficeTableInMemory(use_office_types=False)
        self.offices.read_from_local_file()
        self.disclosures_hostnames = defaultdict(set)
        self.build_office_hostnames()

    def build_office_hostnames(self):
        office: TOfficeInMemory
        self.disclosures_hostnames = defaultdict(set)
        for office in self.offices.offices.values():
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

    def process_offices(self):
        wd = TWikidataRecords()
        wd.read_from_file(self.args.wikidata_info)
        for hostname, wd_infos in wd.hostnames.items():
            r = self.find_wikidata_entry(hostname, wd_infos)
            if r is not None:
                office, wd_info = r
                wikidata_id = os.path.basename(wd_info["item"])
                if office.wikidata_id is None:
                    office.wikidata_id = wikidata_id
                    self.logger.debug("set hostname={} office.name = {} to wikidata = https://www.wikidata.org/wiki/{} , wikidata.title={}".format(
                        hostname, office.name, wikidata_id, wd_info["itemLabel"]))
                elif office.wikidata_id != wikidata_id:
                    self.logger.error("office https://disclosures.ru/office/{} {} has  wikidata_id=https://www.wikidata.org/wiki/{}, "
                                 "but the input file has https://www.wikidata.org/wiki/{}, skip it".format(
                        office.office_id, office.name, office.wikidata_id, wikidata_id))


def main():
    args = parse_args()
    m = TWikiDataMatcher(args)
    m.process_offices()
    m.logger.info("write to {}".format(args.output_file))
    m.offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()