import json
import argparse
import os
import gzip
import pymysql
import logging
from operator import itemgetter
from disclosures_site.declarations.web_sites import TDeclarationWebSites, TDeclarationWebSite
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser()
    return parser.parse_args()


def setup_logging(logfilename="update_offices.log"):
    logger = logging.getLogger("export")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


class TOfficeJoiner:
    def __init__(self):
        self.logger = setup_logging()
        self.logger.debug("start joining")

        self.region_name_to_id = None
        self.fgup = None
        self.website_to_most_freq_office = None
        self.offices_file_path = os.path.join(os.path.dirname(__file__), "../data/offices.txt")
        self.offices = None
        self.web_sites = TDeclarationWebSites(self.logger)
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
                                        unix_socket="/var/run/mysqld/mysqld.sock")
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
            web_site = TDeclarationWebSites.get_web_domain_by_url(url)
            if len(web_site) > 0:
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
                                        unix_socket="/var/run/mysqld/mysqld.sock")
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
                        select  id, name_ru, type_id, parent_id, region_id, url 
                        from declarations_office
        """)
        max_id = max(o['id'] for o in self.offices if o['id'] < TDeclarationWebSites.disclosures_office_start_id)
        new_offices_count = 0
        for id, name_ru, type_id, parent_id, region_id, url in in_cursor:
            if id > max_id:
                r = {
                    'id': id,
                    'name_ru': name_ru,
                    'type_id': type_id,
                    'parent_id': parent_id,
                    'region_id': region_id,
                    'url': url
                }
                new_offices_count += 1
                self.offices.append(r)
        db_connection.close()

        self.logger.debug("found {} new  offices in  declarator".format(new_offices_count))

    def read_regions(self):
        file_path = os.path.join(os.path.dirname(__file__), "../data/regions.txt.gz")
        with gzip.open(file_path) as inp:
            regions = json.load(inp)

            self.region_name_to_id = dict ((r['name'].lower().strip('*'), r['id']) for r in regions)
            self.logger.debug("read {} regions from {}".format(len(self.region_name_to_id), file_path))

    def read_fgup(self):
        file_path = os.path.join(os.path.dirname(__file__), "../data/fgup.txt")
        self.fgup = dict()
        with open (file_path, "r") as inp:
            for line in inp:
                (name, region, web_site) = line.strip().split("\t")
                self.fgup[web_site] =  {
                    "name_ru": name,
                    "region_id": self.region_name_to_id[region.lower()],
                    'type_id': None,
                    'parent_id': None
                    }
        self.logger.debug("read {} fgup from {}".format(len(self.region_name_to_id), file_path))

    def extend_offices_and_sites(self, new_office_dict):
        name_to_office = dict((o['name_ru'], o['id']) for o in self.offices)
        max_id = max (o['id'] for o in self.offices)
        if max_id < TDeclarationWebSites.disclosures_office_start_id:
            max_id = TDeclarationWebSites.disclosures_office_start_id

        for web_site, office_info in new_office_dict.items():
            office_id = name_to_office.get(office_info['name_ru'])
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
                    office_info['name_ru'], web_site, office_id))
            elif has_name and not has_web_site:
                self.web_sites.add_web_site(web_site, office_id)
            else:
                self.logger.error ("cannot add office {} with website {}, there is an office "
                            "with the same name or with the same web_site".format(office_info['name_ru'], web_site))

    def build_offices_and_web_sites (self):
        args = parse_args()
        self.read_offices()
        self.read_regions()
        self.read_fgup()
        self.update_offices_from_declarator()
        self.web_sites.update_from_office_urls(self.offices, self.logger)
        self.calc_office_by_web_domain()
        self.web_sites.add_new_websites_from_declarator(self.website_to_most_freq_office)
        self.extend_offices_and_sites(self.fgup)

        self.web_sites.save_to_disk()
        self.write_offices()
        self.logger.info("do not forget to commit changes to git")


if __name__ == '__main__':
    joiner = TOfficeJoiner()
    joiner.build_offices_and_web_sites()


