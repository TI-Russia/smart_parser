import urllib.parse

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
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, move, mark_large_sites, check_alive, print_urls")
    parser.add_argument("--input-file", dest='input_file', required=True)
    parser.add_argument("--output-file", dest='output_file', required=True)
    parser.add_argument("--url-list", dest='url_list', required=False)
    parser.add_argument("--take-all-web-sites", dest='take_all_web_sites', required=False, action="store_true", default=False,
                        help="by default we skip all abandoned web sites")
    parser.add_argument("--filter-regex", dest='filter_regex', required=False)
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

    def check_web_site_filters(self, web_domain):
        if self.args.filter_regex is not None:
            if re.search(self.args.filter_regex, web_domain) is None:
                return False

        site_info = self.in_web_sites.get_web_site(web_domain)
        if site_info is None:
            self.logger.error("skip {}, cannot find this site".format(web_domain))
            return False
        else:
            if self.args.take_all_web_sites or TWebSiteReachStatus.can_communicate(site_info.reach_status):
                return True
            else:
                self.logger.debug("skip abandoned {}".format(web_domain))
                return False

    def get_url_list(self):
        web_domains = list()
        if self.args.url_list is not None:
            self.logger.info("read url list from {}".format(self.args.url_list))
            with open(self.args.url_list) as inp:
                for url in inp: 
                    url = url.strip(" \r\n")
                    if url.startswith('http'):
                        web_domains.append(urllib.parse.urlsplit(url).netloc)
                    else:
                        web_domains.append(url)
        else:
            #take all web domains
            web_domains = list(self.in_web_sites.web_sites.keys())

        for w in web_domains:
            if self.check_web_site_filters(w):
                yield w

    def ban_sites(self):
        self.out_web_sites.web_sites = self.in_web_sites.web_sites
        cnt = 0
        for url in self.get_url_list():
            self.logger.debug("ban {}".format(url))
            self.out_web_sites.get_web_site(url).ban()
            cnt += 1
        self.logger.info("ban {} web sites".format(cnt))

    def to_utf8(self):
        for k,v in self.in_web_sites.web_sites.items():
            if TUrlUtf8Encode.is_idna_string(k):
                k = TUrlUtf8Encode.from_idna(k)
            self.out_web_sites.web_sites[k] = v

    def move(self):
        assert self.args.filter_regex is not None
        assert self.args.replace_substring is not None
        cnt = 0
        self.out_web_sites.web_sites = deepcopy(self.in_web_sites.web_sites)
        for web_domain in self.get_url_list():
            site_info = self.out_web_sites.get_web_site(web_domain)
            new_web_domain = re.sub(self.args.filter_regex, self.args.replace_substring, web_domain)
            assert new_web_domain != web_domain
            if not self.out_web_sites.has_web_site(new_web_domain):
                self.logger.info("{} -> {}".format(web_domain, new_web_domain))
                self.out_web_sites.web_sites[new_web_domain] = deepcopy(site_info)
            assert self.out_web_sites.get_web_site(new_web_domain).calculated_office_id == site_info.calculated_office_id
            site_info.set_redirect(new_web_domain)
            cnt += 1
        self.logger.info("{} redirects made".format(cnt))

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

    def check_alive_one_site(self, project, url):
        self.logger.info("check {}".format(url))
        web_site = TWebSiteCrawlSnapshot(project, morda_url=url)
        web_site.fetch_the_main_page(enable_search_engine=False)
        if TWebSiteReachStatus.can_communicate(web_site.reach_status):
            return web_site
        else:
            return None

    def check_alive(self):
        self.logger.info("rm {}".format(TDownloadEnv.FILE_CACHE_FOLDER))
        TDownloadEnv.clear_cache_folder()
        self.out_web_sites.web_sites = deepcopy(self.in_web_sites.web_sites)
        complete_bans = list()
        project_path = "project.txt"
        TRobotProject.create_project("dummy.ru", project_path)
        only_selenium_sites = list()
        with TRobotProject(self.logger, project_path, [], "result") as project:
            for web_domain in self.get_url_list():
                site_info: TDeclarationWebSite
                site_info = self.out_web_sites.get_web_site(web_domain)
                web_site = self.check_alive_one_site(project, web_domain)
                if web_site is None:
                    self.logger.info("     {} is dead".format(web_domain))
                    site_info.ban()
                    complete_bans.append(web_domain)
                else:
                    if not web_site.enable_urllib:
                        only_selenium_sites.append(web_domain)
                        self.logger.debug('   {} is only selenium'.format(web_domain))
                    if web_site.web_domain != web_domain:
                        self.logger.info('   {} is alive, but is redirected to {}, protocol = {}'.format(
                            web_domain, web_site.web_domain, web_site.protocol))
                        if not self.out_web_sites.has_web_site(web_site.web_domain):
                            self.out_web_sites.web_sites[web_site.web_domain] = deepcopy(site_info)
                        main_site_info = self.out_web_sites.get_web_site(web_site.web_domain)
                        main_site_info.set_protocol(web_site.protocol)
                        site_info.set_redirect(web_site.web_domain)
                    else:
                        self.logger.info("     {} is alive, protocol = {}, morda = {}".format(
                            web_domain, web_site.protocol, web_site.web_domain))
                        site_info.set_protocol(web_site.protocol)

        os.unlink(project_path)
        self.logger.info("ban {} web sites, only selenium sites: {}".format(len(complete_bans), len(only_selenium_sites)))

    def print_keys(self):
        for web_domain in self.get_url_list():
            print(web_domain)

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
        elif self.args.action == "print_keys":
            self.print_keys()
        else:
            raise Exception("unknown action")
        self.out_web_sites.save_to_disk()


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
