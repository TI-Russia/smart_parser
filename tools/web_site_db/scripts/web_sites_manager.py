from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.web_site_status import TWebSiteReachStatus
from common.primitives import  TUrlUtf8Encode
from common.logging_wrapper import setup_logging

from copy import deepcopy
import argparse
import pymysql
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, mvd, mark_large_sites")
    parser.add_argument("--input-file", dest='input_file', required=True)
    parser.add_argument("--output-file", dest='output_file', required=True)
    parser.add_argument("--ban-list", dest='ban_list', required=False)
    return parser.parse_args()


class TWebSitesManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("web_sites")
        self.in_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.input_file)
        self.in_web_sites.load_from_disk()
        self.out_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.output_file)

    def ban_sites(self):
        with open(self.args.ban_list) as inp:
            self.out_web_sites.web_sites = self.in_web_sites.web_sites
            for x in inp:
                x = x.strip(" \r\n")
                if self.out_web_sites.has_web_site(x):
                    self.out_web_sites.set_status_to_web_site(x, TWebSiteReachStatus.abandoned)
                else:
                    self.out_web_sites.logger.error("skip {}, cannot find this site".format(x))

    def to_utf8(self):
        for k,v in self.in_web_sites.web_sites.items():
            if TUrlUtf8Encode.is_idna_string(k):
                k = TUrlUtf8Encode.from_idna(k)
            self.out_web_sites.web_sites[k] = v

    def convert_mvd(self):
        for k, v in self.in_web_sites.web_sites.items():
            self.out_web_sites.web_sites[k] = v
            if k.endswith('.mvd.ru'):
                key = k[:-len('.mvd.ru')] + '.мвд.рф'
                if key not in self.in_web_sites.web_sites:
                    self.out_web_sites.web_sites[key] = deepcopy(v)
                v.reach_status = TWebSiteReachStatus.abandoned
            self.out_web_sites.web_sites[k] = v

    def mark_large_sites(self):
        db_connection = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
        in_cursor = db_connection.cursor()
        in_cursor.execute("""
                select r.web_domain, count(*) 
                from declarations_source_document d 
                join declarations_section s on s.source_document_id = d.id  
                join declarations_web_reference r on r.source_document_id = d.id 
                where s.income_year={} 
                group by r.web_domain 
                having count(s.id) > 500
                """.format(datetime.now().year - 2))
        self.out_web_sites.web_sites = self.in_web_sites.web_sites
        for web_domain, count in in_cursor:
            if web_domain.find('rospotrebnadzor.ru') != -1:
                continue
            if not self.out_web_sites.has_web_site(web_domain):
                self.logger.debug("cannot find website {} ".format(web_domain))
            else:
                site = self.out_web_sites.get_web_site(web_domain)
                site.dlrobot_max_time_coeff = 2.0

    def main(self):
        if self.args.action == "ban":
            self.ban_sites()
        elif self.args.action == "to_utf":
            self.to_utf8()
        elif self.args.action == "mvd":
            self.convert_mvd()
        elif self.args.action == "mark_large_sites":
            self.mark_large_sites()
        else:
            raise Exception("unknown action")
        self.out_web_sites.save_to_disk()


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
