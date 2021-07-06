from web_site_db.web_sites import TDeclarationWebSiteList, TDeclarationWebSite
from web_site_db.web_site_status import TWebSiteReachStatus
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from web_site_db.robot_project import TRobotProject
from common.primitives import  TUrlUtf8Encode
from common.logging_wrapper import setup_logging
from common.http_request import THttpRequester
from common.download import TDownloadEnv

from copy import deepcopy
import argparse
import pymysql
from datetime import datetime
import re
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, move, mark_large_sites, check_alive")
    parser.add_argument("--input-file", dest='input_file', required=True)
    parser.add_argument("--output-file", dest='output_file', required=True)
    parser.add_argument("--ban-list", dest='ban_list', required=False)
    parser.add_argument("--filter-regex", dest='filter_regex', required=False)
    parser.add_argument("--force", dest='force', required=False, action="store_true", default=False)
    parser.add_argument("--replace-substring", dest='replace_substring', required=False,
                        help="for example, --action move --filter-regex '.mvd.ru$'  --replace-substring .мвд.рф")
    return parser.parse_args()



class TWebSitesManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("web_sites")
        self.in_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.input_file)
        self.in_web_sites.load_from_disk()
        self.out_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.output_file)
        THttpRequester.initialize(self.logger)

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

    def move(self):
        assert self.args.filter_regex is not None
        assert self.args.replace_substring is not None
        cnt = 0
        for k, v in self.in_web_sites.web_sites.items():
            self.out_web_sites.web_sites[k] = v
            if re.match(self.args.filter_regex, k) is not None:
                new_key = re.sub(self.args.filter_regex, self.args.replace_substring, k)
                #new_key = k[:-len('.mvd.ru')] + '.мвд.рф'
                if new_key not in self.in_web_sites.web_sites:
                    self.logger("{} -> {}".format(k, new_key))
                    self.out_web_sites.web_sites[new_key] = deepcopy(v)
                    cnt += 1
                v.reach_status = TWebSiteReachStatus.abandoned
            self.out_web_sites.web_sites[k] = v
        self.logger.info("{} replacements made".format(cnt))

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

    def check_alive_one_site(self, project, url, site_info: TDeclarationWebSite):
        self.logger.info("check {}".format(url))
        web_site = TWebSiteCrawlSnapshot(project, morda_url=url)
        web_site.fetch_the_main_page(enable_search_engine=False)
        if TWebSiteReachStatus.can_communicate(web_site.reach_status):
            self.logger.info("     {} is alive, protocol = {}".format(url, web_site.protocol))
            site_info.http_protocol = web_site.protocol
            return True
        else:
            self.logger.info("     {} is dead".format(url))
            return False

    def check_alive(self, status=TWebSiteReachStatus.abandoned):
        assert self.args.filter_regex is not None
        self.logger.info("rm {}".format(TDownloadEnv.FILE_CACHE_FOLDER))
        TDownloadEnv.clear_cache_folder()
        self.out_web_sites.web_sites = self.in_web_sites.web_sites
        cnt = 0
        project_path = "project.txt"
        TRobotProject.create_project("dummy.ru", project_path)
        with TRobotProject(self.logger, project_path, [], "result") as project:
            for web_domain, site_info in self.out_web_sites.web_sites.items():
                if re.search(self.args.filter_regex, web_domain) is not None:
                    if not self.args.force and not TWebSiteReachStatus.can_communicate(site_info.reach_status):
                        self.logger.info("skip {}".format(web_domain))
                    elif not self.check_alive_one_site(project, web_domain, site_info):
                        site_info.reach_status = status
                        cnt += 1
        os.unlink(project_path)
        self.logger.info("set {} web sites status to {}".format(cnt, status))

    def main(self):
        if self.args.action == "ban":
            self.ban_sites()
        elif self.args.action == "to_utf":
            self.to_utf8()
        elif self.args.action == "move":
            self.move()
        elif self.args.action == "mark_large_sites":
            self.mark_large_sites()
        elif self.args.action == "check_alive":
            self.check_alive()
        else:
            raise Exception("unknown action")
        self.out_web_sites.save_to_disk()


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
