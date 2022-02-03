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


def get_office_hostnames(offices: TOfficeTableInMemory):
    office: TOfficeInMemory
    disclosures_hostnames = defaultdict(set)
    for office in offices.offices.values():
        site_info: TDeclarationWebSite
        for site_info in office.office_web_sites:
            if site_info.can_communicate():
                disclosures_hostnames[get_web_domain(site_info.url)].add(office)
    return disclosures_hostnames


def process_offices(args, logger, offices: TOfficeTableInMemory):
    disclosures_hostnames = get_office_hostnames(offices)
    wd = TWikidataRecords()
    wd.read_from_file(args.wikidata_info)
    for hostname, wd_infos in wd.hostnames.items():
        if len(wd_infos) > 1:
            logger.debug("{} is ambigous in wikidata".format(hostname))
            continue

        found = disclosures_hostnames.get(hostname, list())
        if len(found) == 0:
            logger.debug("cannot find {} in disclosures".format(hostname))
        elif len(found) > 1:
            logger.debug("hostname  {} is ambiguous".format(hostname))
        else:
            wikidata_id = os.path.basename(wd_infos[0]["item"])
            office = list(found)[0]
            if office.wikidata_id is None:
                office.wikidata_id = wikidata_id
                logger.debug("set wikidata for {} to {}".format(office.name, wikidata_id))
            elif office.wikidata_id != wikidata_id:
                logger.error("office https://disclosures.ru/office/{} {} has  wikidata_id=https://www.wikidata.org/wiki/{}, "
                             "but the input file has https://www.wikidata.org/wiki/{}, skip it".format(
                    office.office_id, office.name, office.wikidata_id, wikidata_id))


def main():
    args = parse_args()
    logger = setup_logging("wd_by_url")
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()
    process_offices(args, logger, offices)
    logger.info("write to {}".format(args.output_file))
    offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()