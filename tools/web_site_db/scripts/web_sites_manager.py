from web_site_db.web_sites import TDeclarationWebSiteList, TDeclarationWebSite
from web_site_db.web_site_status import TWebSiteReachStatus
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from web_site_db.robot_project import TRobotProject
from common.primitives import  TUrlUtf8Encode, strip_scheme_and_query
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
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, move, mark_large_sites, check_alive, "
                                                        "print_urls, check, redirect_subdomain")
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
        self.temp_dlrobot_project = None
        THttpRequester.initialize(self.logger)

    def check_web_site_filters(self, site_url):
        if self.args.filter_regex is not None:
            if re.search(self.args.filter_regex, site_url) is None:
                return False

        site_info = self.in_web_sites.get_web_site(site_url)
        if site_info is None:
            self.logger.error("skip {}, cannot find this site".format(site_url))
            return False
        else:
            if self.args.take_all_web_sites or TWebSiteReachStatus.can_communicate(site_info.reach_status):
                return True
            else:
                self.logger.debug("skip abandoned {}".format(site_url))
                return False

    def get_url_list(self, start_selenium=False):
        web_domains = list()
        if self.args.url_list is not None:
            self.logger.info("read url list from {}".format(self.args.url_list))
            with open(self.args.url_list) as inp:
                for url in inp:
                    url = url.strip(" \r\n")
                    if url.startswith('http'):
                        web_domains.append(strip_scheme_and_query(url))
                    else:
                        web_domains.append(url)
        else:
            #take all web domains
            web_domains = list(self.in_web_sites.web_sites.keys())

        domains_filtered = (w for w in web_domains if self.check_web_site_filters(w))
        if start_selenium:
            self.logger.info("rm {}".format(TDownloadEnv.FILE_CACHE_FOLDER))
            TDownloadEnv.clear_cache_folder()
            project_path = "project.txt"
            TRobotProject.create_project("dummy.ru", project_path)
            with TRobotProject(self.logger, project_path, [], "result") as self.temp_dlrobot_project:
                for w in domains_filtered:
                    yield w
            os.unlink(project_path)
        else:
            for w in domains_filtered:
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
        self.out_web_sites.web_sites = deepcopy(self.in_web_sites.web_sites)
        cnt = 0
        for site_url in self.get_url_list():
            site_info = self.out_web_sites.get_web_site(site_url)
            if site_info.redirect_to is not None and TUrlUtf8Encode.is_idna_string(site_info.redirect_to):
                site_info.redirect_to = TUrlUtf8Encode.from_idna(site_info.redirect_to)
                if site_info.redirect_to == site_url and site_info.reach_status == TWebSiteReachStatus.abandoned:
                    site_info.redirect_to = None
                    site_info.reach_status = TWebSiteReachStatus.normal
                cnt += 1
            if TUrlUtf8Encode.is_idna_string(site_url):
                del self.out_web_sites.web_sites[site_url]
                site_url = TUrlUtf8Encode.from_idna(site_url)
                self.out_web_sites.web_sites[site_url] = site_info
                cnt += 1
        self.logger.info("{} conversions made".format(cnt))

    def move(self):
        assert self.args.filter_regex is not None
        assert self.args.replace_substring is not None
        cnt = 0
        self.out_web_sites.web_sites = deepcopy(self.in_web_sites.web_sites)
        for site_url in self.get_url_list():
            site_info = self.out_web_sites.get_web_site(site_url)
            new_web_domain = re.sub(self.args.filter_regex, self.args.replace_substring, site_url)
            assert new_web_domain != site_url
            if not self.out_web_sites.has_web_site(new_web_domain):
                self.logger.info("{} -> {}".format(site_url, new_web_domain))
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

    def check_alive_one_site(self,  url):
        self.logger.info("check {}".format(url))
        web_site = TWebSiteCrawlSnapshot(self.temp_dlrobot_project, morda_url=url)
        web_site.fetch_the_main_page(enable_search_engine=False)
        if TWebSiteReachStatus.can_communicate(web_site.reach_status):
            return web_site
        else:
            return None

    def check_alive(self):
        self.out_web_sites.web_sites = deepcopy(self.in_web_sites.web_sites)
        complete_bans = list()
        only_selenium_sites = list()
        for site_url in self.get_url_list(start_selenium=True):
            site_info: TDeclarationWebSite
            site_info = self.out_web_sites.get_web_site(site_url)
            web_site = self.check_alive_one_site(site_url)
            if web_site is None:
                self.logger.info("     {} is dead".format(site_url))
                site_info.ban()
                complete_bans.append(site_url)
            else:
                if not web_site.enable_urllib:
                    only_selenium_sites.append(site_url)
                    self.logger.debug('   {} is only selenium'.format(site_url))
                new_site_url = strip_scheme_and_query(web_site.main_page_url)
                if new_site_url != site_url:
                    self.logger.info('   {} is alive, but is redirected to {}, protocol = {}'.format(
                        site_url, new_site_url, web_site.protocol))
                    if not self.out_web_sites.has_web_site(new_site_url):
                        self.out_web_sites.web_sites[new_site_url] = deepcopy(site_info)
                    site_info.set_redirect(new_site_url)
                    site_info = self.out_web_sites.get_web_site(new_site_url)
                else:
                    self.logger.info("     {} is alive, protocol = {}, main_page_url = {}".format(
                        site_url, web_site.protocol, web_site.main_page_url))
                site_info.set_protocol(web_site.protocol)
                site_info.set_title(web_site.get_title(web_site.main_page_url))


        self.logger.info("ban {} web sites, only selenium sites: {}".format(len(complete_bans), len(only_selenium_sites)))

    def print_keys(self):
        for web_domain in self.get_url_list():
            print(web_domain)

    def check(self):
        for web_domain in self.get_url_list():
            site_info = self.in_web_sites.get_web_site(web_domain)
            if TWebSiteReachStatus.can_communicate(site_info.reach_status):
                if site_info.http_protocol is None:
                    self.logger.error("{} has no protocol".format(web_domain))
            if site_info.redirect_to is not None:
                if not self.in_web_sites.has_web_site(site_info.redirect_to):
                    self.logger.error("{} has missing redirect {}".format(web_domain, site_info.redirect_to))

    def redirect_subdomain(self):
        for web_domain in self.get_url_list(start_selenium=True):
            site_info = self.in_web_sites.get_web_site(web_domain)
            if site_info.redirect_to is None or not web_domain.endswith(site_info.redirect_to):
                continue
            self.check_alive_one_site(web_domain)

    def main(self):
        if self.args.action == "ban":
            self.ban_sites()
        elif self.args.action == "to_utf8":
            self.to_utf8()
        elif self.args.action == "move":
            self.move()
        elif self.args.action == "mark_large_sites":
            self.mark_large_sites()
        elif self.args.action == "check_alive":
            self.check_alive()
        elif self.args.action == "print_keys":
            self.print_keys()
        elif self.args.action == "check":
            self.check()
        elif self.args.action == "redirect_subdomain":
            self.redirect_subdomain()
        else:
            raise Exception("unknown action")
        self.out_web_sites.save_to_disk()


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
