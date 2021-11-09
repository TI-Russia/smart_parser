!!!! this script must be fully refactored after joining sites and offices !!!!

from office_db.web_site_list import TDeclarationWebSiteList
from common.urllib_parse_pro import get_site_domain_wo_www
from office_db.russian_regions import TRussianRegions
from common.logging_wrapper import setup_logging

import json
import argparse
import os
import pymysql
from operator import itemgetter
from collections import defaultdict


#parts of TDeclarationWebSiteList, must be declared here

def add_new_websites_from_declarator(self, website_to_most_freq_office):
    errors = list()
    for web_site, calculated_office_id in website_to_most_freq_office.items():
        if web_site not in self.web_sites:
            self.add_web_site(web_site, calculated_office_id)
        elif self.web_sites[web_site].calculated_office_id >= self.disclosures_office_start_id:
            errors.append("web site: {}, declarator office id: {}, disclosures office id: {}".format(
                web_site, calculated_office_id, self.web_sites[web_site].calculated_office_id))
    if len(errors) > 0:
        file_name = "conflict_offices.txt"
        with open(file_name, "w") as outp:
            for x in errors:
                outp.write(x + "\n")
        raise Exception(
            "there are web sites that are referenced in disclosures web_site_snapshots and declarator web_site_snapshots" +
            "we have to office ambiguity. These web sites are written to {}".format(file_name))


def update_from_office_urls(self, offices, logger):
    for o in offices:
        web_site = strip_scheme_and_query(o.get('url'))
        if web_site not in self.web_sites:
            self.add_web_site(web_site, o['id'])
            logger.info('add a website {} from office.url'.format(web_site))



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--declarator-host", dest='declarator_host', default='localhost')
    parser.add_argument("--action", dest='action', default='all', help="can be all")
    return parser.parse_args()


class TOfficeJoiner:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="update_offices.log")
        self.logger.debug("start joining")
        self.regions = TRussianRegions()
        self.region_name_to_id = None
        self.website_to_most_freq_office = None
        self.offices_file_path = os.path.join(os.path.dirname(__file__), "../data/offices.txt")
        self.offices = None
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.web_sites.load_from_disk()

    def read_offices (self):
        with open(self.offices_file_path) as inp:
            self.offices = json.load(inp)

    def write_offices (self):
        with open(self.offices_file_path, "w") as outp:
            json.dump(self.offices, outp,  ensure_ascii=False, indent=4)

    def calc_office_by_web_domain(self):
        # query to declarator db
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        host=self.args.declarator_host
                                        )
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
                        select  o.id,
                                f.link 
                        from declarations_office o
                        join declarations_document d on o.id = d.office_id
                        join declarations_documentfile f on d.id = f.document_id
        """)
        web_site_and_office_freq = defaultdict(int)
        for office_id, url in in_cursor:
            if len(url) == 0:
                continue
            web_site = get_site_domain_wo_www(url)
            if len(web_site.strip()) > 2 and web_site.find(' ') == -1 and web_site.find('.') != -1 and \
                    web_site != "example.com":
                web_site_and_office_freq[(web_site, office_id)] += 1
        freq_list = sorted(web_site_and_office_freq.items(), key=itemgetter(1), reverse=True)
        self.website_to_most_freq_office = dict()
        for (website, office_id), freq in freq_list:
            if website not in self.website_to_most_freq_office:
                self.website_to_most_freq_office[website] = office_id
        db_connection.close()
        self.logger.debug("build office_by_web_domain mapping from declarator of {} pairs".format(len(self.website_to_most_freq_office)))

    def update_offices_from_declarator(self):
        db_connection = pymysql.connect(db="declarator", user="declarator", password="declarator",
                                        host=self.args.declarator_host)
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
                        select  id, name_ru, type_id, parent_id, region_id, url 
                        from declarations_office
        """)
        max_id = max(o['id'] for o in self.offices if o['id'] < TDeclarationWebSiteList.disclosures_office_start_id)
        new_offices_count = 0
        for id, name_ru, type_id, parent_id, region_id, url in in_cursor:
            if id > max_id:
                r = {
                    'id': id,
                    'name': name_ru,
                    'type_id': type_id,
                    'parent_id': parent_id,
                    'region_id': region_id,
                    'url': url
                }
                new_offices_count += 1
                self.offices.append(r)
        db_connection.close()

        self.logger.debug("found {} new  web_site_snapshots in  declarator".format(new_offices_count))

    def read_fgup(self):
        file_path = os.path.join(os.path.dirname(__file__), "../../disclosures_site/data/fgup.txt")
        fgup = dict()
        with open (file_path, "r") as inp:
            for line in inp:
                (name, region, web_site) = line.strip().split("\t")
                fgup[web_site] =  {
                    "name": name,
                    "region_id": self.regions.get_region_in_nominative(region.lower()).id,
                    'type_id': None,
                    'parent_id': None
                    }
        self.logger.debug("read {} fgup from {}".format(len(fgup), file_path))
        return fgup

    def read_sudrf(self):
        file_path = os.path.join(os.path.dirname(__file__), "../../disclosures_site/data/sudrf.txt")
        output_courts = dict()
        with open(file_path, "r") as inp:
            courts = json.load(inp)

        for court in courts:
            web_site = get_site_domain_wo_www(court['link'])
            output_courts[web_site] = {
                "name": court['name'],
                "region_id": self.regions.get_region_in_nominative(court['region']),
                'type_id': None,
                'parent_id': None
                }
        self.logger.debug("read {} courts from {}".format(len(courts), file_path))
        return output_courts

    def extend_offices_and_sites(self, new_office_dict):
        name_to_office = dict((o['name'], o['id']) for o in self.offices)
        max_id = max (o['id'] for o in self.offices)
        if max_id < TDeclarationWebSiteList.disclosures_office_start_id:
            max_id = TDeclarationWebSiteList.disclosures_office_start_id

        for web_site, office_info in new_office_dict.items():
            office_id = name_to_office.get(office_info['name'])
            has_web_site = self.web_sites.has_web_site(web_site)
            has_name = office_id is not None
            if has_web_site and has_name and \
                    self.web_sites.get_web_site(web_site).calculated_office_id == office_id:
                pass # old information, no change
            elif not has_name and not has_web_site:
                max_id += 1
                office_id = max_id
                office_info['id'] = office_id
                self.offices.append(office_info)
                self.web_sites.add_web_site(web_site, office_id)
                self.logger.debug("add a new office {} with a new web site {}, set office_id={}".format(
                    office_info['name'], web_site, office_id))
            elif has_name and not has_web_site:
                self.web_sites.add_web_site(web_site, office_id)
            else:
                self.logger.error ("cannot add office {} with website {}, there is an office "
                            "with the same name or with the same web_site".format(office_info['name'], web_site))

    """
    wd:Q2198484  - районы
    wd:Q634099 - муниципальные образования

    SELECT ?itemLabel ?website ?sitelinks
    WHERE
    {
      VALUES ?russian_district { wd:Q2198484 wd:Q634099}
      ?item wdt:P31 ?russian_district.
      ?item wdt:P856 ?website.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ru". }
    }
    """
    def read_districts_from_wikidata (self):
        file_path = os.path.join(os.path.dirname(__file__), "../../disclosures_site/data/districts_from_wikidata.json")
        districts = dict()
        with open(file_path, "r") as inp:
            for x in json.load(inp):
                name = x['itemLabel']
                web_site = get_site_domain_wo_www(x['website'])
                districts[web_site] =  {
                    "name": name,
                    "region_id": None,
                    'type_id': None,
                    'parent_id': None
                    }
        self.logger.info("read {} items from {}".format(len(districts), file_path))
        return districts

    def build_offices_and_web_sites (self):
        self.read_offices()

        self.logger.info("update_offices_from_declarator")
        self.update_offices_from_declarator()

        self.logger.info("update_from_office_urls")
        self.web_sites.update_from_office_urls(self.offices, self.logger)

        self.logger.info("calc_office_by_web_domain")
        self.calc_office_by_web_domain()

        self.logger.info("add_new_websites_from_declarator")
        self.web_sites.add_new_websites_from_declarator(self.website_to_most_freq_office)

        self.logger.info("extend_offices_and_sites(self.read_fgup())")
        self.extend_offices_and_sites(self.read_fgup())

        self.logger.info("extend_offices_and_sites(self.read_districts_from_wikidata())")
        self.extend_offices_and_sites(self.read_districts_from_wikidata())

        self.logger.info("extend_offices_and_sites(self.read_sudrf())")
        self.extend_offices_and_sites(self.read_sudrf())

        self.web_sites.save_to_disk()
        self.write_offices()
        self.logger.info("do not forget to commit changes to git")


def main():

    args = parse_args()
    joiner = TOfficeJoiner(args)
    if args.action == "all":
        joiner.build_offices_and_web_sites()
    else:
        raise Exception("unknown action")


if __name__ == '__main__':
    main()

