from office_db.web_site_list import TDeclarationWebSiteList
from office_db.declaration_office_website import TDeclarationWebSite
from common.web_site_status import TWebSiteReachStatus
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from web_site_db.robot_project import TRobotProject
from common.urllib_parse_pro import strip_scheme_and_query, TUrlUtf8Encode
from common.logging_wrapper import setup_logging
from common.http_request import THttpRequester
from common.download import TDownloadEnv
from office_db.offices_in_memory import TOfficeInMemory
from common.serp_parser import SearchEngine, SearchEngineEnum


import random
import argparse
import re
import os
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, move, mark_large_sites, check_alive, "
                                                        "print_urls, check, redirect_subdomain, regional_to_main")
    parser.add_argument("--output-file", dest='output_file', required=True)
    parser.add_argument("--url-list", dest='url_list', required=False)
    parser.add_argument("--take-all-web-sites", dest='take_all_web_sites', required=False, action="store_true", default=False,
                        help="by default we skip all abandoned web sites")
    parser.add_argument("--filter-regex", dest='filter_regex', required=False)
    parser.add_argument("--replace-substring", dest='replace_substring', required=False,
                        help="for example, --action move --filter-regex '.mvd.ru$'  --replace-substring .мвд.рф")
    parser.add_argument("--parent-office-id", dest='parent_office_id', type=int, required=False)
    parser.add_argument("--query-template", dest='query_template', required=False)
    return parser.parse_args()


class TWebSitesManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("web_sites")
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.temp_dlrobot_project: TRobotProject
        self.temp_dlrobot_project = None
        THttpRequester.initialize(self.logger)

    def check_web_site_filters(self, site_url):
        if site_url.strip() == "":
            return False

        if self.args.filter_regex is not None:
            if re.search(self.args.filter_regex, site_url) is None:
                return False

        site_info = self.web_sites.get_web_site(site_url)
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
            web_domains = list(self.web_sites.web_sites.keys())

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
        cnt = 0
        for url in self.get_url_list():
            self.logger.debug("ban {}".format(url))
            self.web_sites.get_web_site(url).ban()
            cnt += 1
        self.logger.info("ban {} web sites".format(cnt))

    def to_utf8(self):
        cnt = 0
        for site_url in self.get_url_list():
            site_info = self.web_sites.get_web_site(site_url)
            if site_info.redirect_to is not None and TUrlUtf8Encode.is_idna_string(site_info.redirect_to):
                site_info.redirect_to = TUrlUtf8Encode.convert_url_from_idna(site_info.redirect_to)
                if site_info.redirect_to == site_url and site_info.reach_status == TWebSiteReachStatus.abandoned:
                    site_info.redirect_to = None
                    site_info.reach_status = TWebSiteReachStatus.normal
                cnt += 1
            if TUrlUtf8Encode.is_idna_string(site_url):
                site_info.url = TUrlUtf8Encode.convert_url_from_idna(site_url)
                cnt += 1
        self.logger.info("{} conversions made".format(cnt))

    def check_alive_one_site(self,  url):
        self.logger.info("check {}".format(url))
        web_site = TWebSiteCrawlSnapshot(self.temp_dlrobot_project, morda_url=url)
        web_site.fetch_the_main_page(enable_search_engine=False)
        if TWebSiteReachStatus.can_communicate(web_site.reach_status):
            return web_site
        else:
            self.logger.info("restart selenium, and try again")
            self.temp_dlrobot_project.selenium_driver.restart()
            web_site = TWebSiteCrawlSnapshot(self.temp_dlrobot_project, morda_url=url)
            web_site.fetch_the_main_page(enable_search_engine=False)
            if TWebSiteReachStatus.can_communicate(web_site.reach_status):
                return web_site
            else:
                return None

    def check_alive_one_url(self, site_url, complete_bans):
        site_info: TDeclarationWebSite
        site_info = self.web_sites.get_web_site(site_url)
        web_site = self.check_alive_one_site(site_url)
        office = self.web_sites.get_office(site_url)
        if web_site is None:
            self.logger.info("     {} is dead".format(site_url))
            site_info.ban()
            complete_bans.append(site_url)
        else:
            new_site_url = web_site.get_main_url_protocol() + "://" + strip_scheme_and_query(web_site.main_page_url)
            title = web_site.get_title(web_site.main_page_url)
            if new_site_url != site_url:
                self.logger.info('   {} is alive, but is redirected to {}'.format(site_url, new_site_url))
                new_site_info = None
                for u in office.office_web_sites:
                    if u.url == site_url:
                        u.set_redirect(new_site_url)
                    if u.url == new_site_url:
                        new_site_info = u
                if new_site_info is None:
                    new_site_info = TDeclarationWebSite(url=new_site_url)
                    office.office_web_sites.append(new_site_info)
                new_site_info.set_title(title)
            else:
                self.logger.info("     {} is alive, main_page_url = {}".format(
                    site_url, web_site.main_page_url))
                site_info.set_title(title)

    def check_alive(self):
        complete_bans = list()
        for site_url in self.get_url_list(start_selenium=True):
            self.check_alive_one_url(site_url, complete_bans)

        self.logger.info("ban {} web sites".format(len(complete_bans)))

    def print_keys(self):
        for web_domain in self.get_url_list():
            print(web_domain)

    def check(self):
        for web_domain in self.get_url_list():
            site_info = self.web_sites.get_web_site(web_domain)
            if TWebSiteReachStatus.can_communicate(site_info.reach_status):
                if not site_info.url.startwith('http'):
                    self.logger.error("{} has no protocol".format(web_domain))
            if site_info.redirect_to is not None:
                if not self.web_sites.has_web_site(site_info.redirect_to):
                    self.logger.error("{} has missing redirect {}".format(web_domain, site_info.redirect_to))

    def redirect_subdomain(self):
        for web_domain in self.get_url_list(start_selenium=True):
            site_info = self.web_sites.get_web_site(web_domain)
            if site_info.redirect_to is None or not web_domain.endswith(site_info.redirect_to):
                continue
            self.check_alive_one_site(web_domain)

    #python3 web_sites_manager.py --action create_departments --input-file data/web_sites.json --output-file data/web_sites.json.1 --parent-office-id 4202 --query-template "спб  {}"
    def create_departments(self):
        o: TOfficeInMemory
        TDownloadEnv.clear_cache_folder()
        project_path = "project.txt"
        TRobotProject.create_project("dummy.ru", project_path)
        with TRobotProject(self.logger, project_path, [], "result") as self.temp_dlrobot_project:
            for o in self.web_sites.offices.values():
                if o.parent_id == self.args.parent_office_id:
                    self.logger.info("ofiice id = {}, {}".format(o.office_id, o.name))
                    query = self.args.query_template.format(o.name)
                    engine = random.choice([SearchEngineEnum.GOOGLE, SearchEngineEnum.YANDEX])
                    results = SearchEngine.send_request(engine, query, self.temp_dlrobot_project.selenium_driver)
                    if len(results) == 0:
                        msg = "cannot find results fo query {}".format(query)
                        self.logger.error(msg)
                    else:
                        new_web_site = TDeclarationWebSite(url=results[0])
                        found = False
                        for u in o.office_web_sites:
                            if u.url == new_web_site:
                                found = True
                                self.logger.error("{} already exists".format(new_web_site))
                        if not found:
                            o.office_web_sites.append(new_web_site)
                            self.check_alive_one_url(new_web_site.url)
                    time.sleep(20)

    def main(self):
        if self.args.action == "ban":
            self.ban_sites()
        elif self.args.action == "to_utf8":
            self.to_utf8()
        elif self.args.action == "check_alive":
            self.check_alive()
        elif self.args.action == "print_keys":
            self.print_keys()
        elif self.args.action == "check":
            self.check()
        elif self.args.action == "redirect_subdomain":
            self.redirect_subdomain()
        elif self.args.action == "create_departments":
            self.create_departments()
        else:
            raise Exception("unknown action")

        self.logger.info("write to {}".format(self.args.output_file))
        self.web_sites.offices.write_to_local_file(self.args.output_file)


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
