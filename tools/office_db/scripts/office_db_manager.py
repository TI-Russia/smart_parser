import json

from office_db.web_site_list import TDeclarationWebSiteList
from office_db.declaration_office_website import TDeclarationWebSite
from common.web_site_status import TWebSiteReachStatus
from dlrobot.common.robot_web_site import TWebSiteCrawlSnapshot
from dlrobot.common.robot_project import TRobotProject
from common.urllib_parse_pro import strip_scheme_and_query, TUrlUtf8Encode, get_site_url
from common.logging_wrapper import setup_logging
from common.http_request import THttpRequester
from common.download import TDownloadEnv
from office_db.offices_in_memory import TOfficeInMemory, TOfficeTableInMemory
from common.serp_parser import SearchEngine, SearchEngineEnum
from common.html_parser import get_html_title

import random
import argparse
import re
import os
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, move, mark_large_sites, check_alive, select, "
                                                        "print_urls, check, redirect_subdomain, regional_to_main, split, make_redirects,"
                                                        "get_title_from_local_files, print_web_sites, check_mirrors, select_adhoc")
    parser.add_argument("--input-offices", dest='input_offices', required=False, default=None,
                        help="default is ~/smart_parser/tools/offices_db/data/offices.txt")
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--redirect-mapping-path", dest='redirect_mapping_path', required=False)
    parser.add_argument("--split-parts", dest='split_parts', type=int, default=100)
    parser.add_argument("--url-list", dest='url_list', required=False)
    parser.add_argument("--take-all-web-sites", dest='take_all_web_sites', required=False, action="store_true", default=False,
                        help="by default we skip all abandoned web sites")
    parser.add_argument("--filter-regex", dest='filter_regex', required=False)
    parser.add_argument("--filter-by-source", dest='filter_by_source', required=False)
    parser.add_argument("--take-without-titles", dest='take_without_titles', required=False, action="store_true", default=False,)
    parser.add_argument("--replace-substring", dest='replace_substring', required=False,
                        help="for example, --action move --filter-regex '.mvd.ru$'  --replace-substring .мвд.рф")
    parser.add_argument("--parent-office-id", dest='parent_office_id', type=int, required=False)
    parser.add_argument("--query-template", dest='query_template', required=False)
    parser.add_argument("--logfile", dest='logfile', default="web_sites.log")
    parser.add_argument("--write-main-page", dest="main_page_path", action="store_true", default=False)
    return parser.parse_args()


class TWebSitesManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging(log_file_name=self.args.logfile)
        if self.args.input_offices is not None:
            offices = TOfficeTableInMemory()
            offices.read_from_local_file(self.args.input_offices)
            self.web_sites = TDeclarationWebSiteList(self.logger, offices=offices)
        else:
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
            if self.args.take_without_titles:
                return TWebSiteReachStatus.can_communicate(site_info.reach_status) and site_info.title is None
            elif self.args.take_all_web_sites or TWebSiteReachStatus.can_communicate(site_info.reach_status):
                return True
            else:
                self.logger.debug("skip abandoned {}".format(site_url))
                return False

    def read_web_domains_from_file(self):
        self.logger.info("read url list from {}".format(self.args.url_list))
        web_domains = list()
        with open(self.args.url_list) as inp:
            for url in inp:
                url = url.strip(" \r\n")
                if url.startswith('http'):
                    web_domains.append(strip_scheme_and_query(url))
                else:
                    web_domains.append(url)
        return web_domains

    def get_url_list(self, start_selenium=False):
        web_domains = list()
        if self.args.filter_by_source is not None:
            web_domains = list()
            for k in self.web_sites.web_sites.values():
                if k.parent_office.source_id == self.args.filter_by_source:
                    web_domains.append(get_site_url(k.url))
        elif self.args.url_list is not None:
            web_domains = self.read_web_domains_from_file()
        else:
            #take all web domains
            web_domains = list(self.web_sites.web_sites.keys())

        domains_filtered = list(w for w in web_domains if self.check_web_site_filters(w))

        self.logger.info("we are going to process {} web sites".format(len(domains_filtered)))

        if start_selenium:
            TDownloadEnv.FILE_CACHE_FOLDER = TDownloadEnv.FILE_CACHE_FOLDER + "_{}_{}".format(time.time(), os.getpid())
            self.logger.info("rm {}".format(TDownloadEnv.FILE_CACHE_FOLDER))
            TDownloadEnv.clear_cache_folder()
            project_path = "project.txt"
            TRobotProject.create_project("dummy.ru", project_path)
            with TRobotProject(self.logger, project_path, export_folder="result") as self.temp_dlrobot_project:
                for w in domains_filtered:
                    yield w
                os.unlink(project_path)
        else:
            for w in domains_filtered:
                yield w

    def ban_sites(self):
        cnt = 0
        for url in self.get_url_list(start_selenium=True):
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

    def browse_one_url(self,  url):
        self.logger.info("check {}".format(url))
        web_site = TWebSiteCrawlSnapshot(self.temp_dlrobot_project, morda_url=url, enable_step_init=False)
        web_site.fetch_the_main_page(enable_search_engine=False)
        if TWebSiteReachStatus.can_communicate(web_site.reach_status):
            return web_site
        else:
            self.logger.info("restart selenium, and try again")
            self.temp_dlrobot_project.selenium_driver.restart()
            web_site = TWebSiteCrawlSnapshot(self.temp_dlrobot_project, morda_url=url, enable_step_init=False)
            web_site.fetch_the_main_page(enable_search_engine=False)
            if TWebSiteReachStatus.can_communicate(web_site.reach_status):
                return web_site
            else:
                return None

    def get_external_file_name_by_site_url(self, site_url):
        return site_url.strip('/').replace('/', '_') + ".page_source.html"

    def check_alive_one_url(self, site_url, complete_bans, site_info=None):
        site_info: TDeclarationWebSite
        if site_info is None:
            site_info = self.web_sites.get_web_site(site_url)
        web_site = self.browse_one_url(site_url)
        #office = self.web_sites.get_office(site_url)
        office = site_info.parent_office
        if web_site is None:
            self.logger.info("     {} is dead".format(site_url))
            site_info.ban()
            complete_bans.append(site_url)
        else:
            new_site_url = web_site.get_main_url_protocol() + "://" + strip_scheme_and_query(web_site.main_page_url)
            title = web_site.get_title(web_site.main_page_url)
            if strip_scheme_and_query(web_site.main_page_url).strip('/') != site_url.strip('/'):
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

            if web_site.main_page_source.lower().find('коррупц') != -1:
                self.logger.info("site contains corruption keyword {}".format(site_url))
                site_info.corruption_keyword_in_html = True

            if self.args.main_page_path:
                try:
                    with open(self.get_external_file_name_by_site_url(site_url), "w") as outp:
                        outp.write(web_site.main_page_source)
                except Exception as exp:
                    self.logger.error("cannot save page html to file: {} ".format(site_url))

    def check_alive(self):
        complete_bans = list()
        checked_count = 0
        for site_url in self.get_url_list(start_selenium=True):
            self.check_alive_one_url(site_url, complete_bans)
            checked_count += 1

        self.logger.info("ban {} web sites out of {} sites".format(len(complete_bans), checked_count))

    def print_keys(self):
        for web_domain in self.get_url_list():
            print(web_domain)

    def split(self):
        parts_count = self.args.split_parts
        chunk_size = int(len(self.web_sites.offices.offices) / parts_count)
        offices = list(self.web_sites.offices.offices.values())
        chunk_id = 0
        cnt = 0
        for l in range(0, len(offices), chunk_size):
            chunk_id += 1
            o = TOfficeTableInMemory()
            for i in offices[l:l + chunk_size]:
                o.add_office(i)
            file_path = "chunk_offices_{}.txt".format(chunk_id)
            o.write_to_local_file(file_path)
            cnt += len (o.offices)
        assert cnt == len(offices)

    def check(self):
        self.web_sites.check_valid(self.logger, fail_fast=False)

    def redirect_subdomain(self):
        for web_domain in self.get_url_list(start_selenium=True):
            site_info = self.web_sites.get_web_site(web_domain)
            if site_info.redirect_to is None or not web_domain.endswith(site_info.redirect_to):
                continue
            self.browse_one_url(web_domain)

    def create_departments(self):
        o: TOfficeInMemory
        TDownloadEnv.clear_cache_folder()
        project_path = "project.txt"
        TRobotProject.create_project("dummy.ru", project_path, web_sites_db=self.web_sites)
        with TRobotProject(self.logger, project_path, export_folder="result") as self.temp_dlrobot_project:
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

    def select(self):
        out = TOfficeTableInMemory()
        for web_domain in self.get_url_list():
            site_info: TDeclarationWebSite
            site_info = self.web_sites.get_web_site(web_domain)
            out.add_office(site_info.parent_office)
        self.web_sites.offices = out

    def select_adhoc(self):
        good_web_domains = set(self.read_web_domains_from_file())
        office: TOfficeInMemory
        ban_cnt = 0
        sp_left = 0
        for office in self.web_sites.offices.offices.values():
            if office.is_from_spravochnik():
                w: TDeclarationWebSite

                for w in office.office_web_sites:
                    if not w.can_communicate():
                        continue
                    u = strip_scheme_and_query(w.url)
                    if u in good_web_domains or "{}/".format(u) in good_web_domains:
                        sp_left += 1
                        continue
                    ban_cnt += 1
                    self.logger.debug("ban office_id={}".format(office.office_id))
                    w.ban(TWebSiteReachStatus.unpromising   )
        self.logger.info("ban {} sites, left in spravochnik {}".format(ban_cnt, sp_left))

    def make_redirects(self):
        with open (self.args.redirect_mapping_path) as inp:
            for l in inp:
                old, new_site_url = l.strip().split()
                if not new_site_url.startswith('http'):
                    raise Exception("unknown http prefix in  {}".format(new_site_url))
                web_site = self.web_sites.search_url(old)
                if web_site is None:
                    raise Exception("cannot find website {}".format(old))
                web_site.set_redirect(new_site_url)
                new_site_info = TDeclarationWebSite(url=new_site_url)
                web_site.parent_office.office_web_sites.append(new_site_info)

    def get_title_from_local_files(self):
        for site_url in self.get_url_list(start_selenium=False):
            site_info = self.web_sites.get_web_site(site_url)
            file_path = os.path.join("page_source",self.get_external_file_name_by_site_url(site_url))
            if os.path.exists(file_path):
                self.logger.info("read {}".format(file_path))
                with open(file_path, "rb") as inp:
                    title = get_html_title(inp.read())
                    site_info.set_title(title)

    def print_web_sites(self):
        site_infos = list()
        for site_url in self.get_url_list(start_selenium=False):
            site_info = self.web_sites.get_web_site(site_url)
            site_info.title = TDeclarationWebSite.clean_title(site_info.title)
            d = site_info.write_to_json()
            d['office_id'] = site_info.parent_office.office_id
            site_infos.append(d)

        print (json.dumps(site_infos, ensure_ascii=False, indent=4))

    def check_mirrors(self):
        offices = set()
        complete_bans = list()
        for site_url in self.get_url_list(start_selenium=True):
            office_info: TOfficeInMemory
            office_info = self.web_sites.get_web_site(site_url).parent_office
            not_abandoned_cnt = 0
            for u in office_info.office_web_sites:
                if u.can_communicate():
                    not_abandoned_cnt += 1
            if not_abandoned_cnt > 1 and office_info.office_web_sites[-1].can_communicate() and office_info not in offices:
                offices.add(office_info)
                for i in range(len(office_info.office_web_sites) - 1):
                    site_info = office_info.office_web_sites[i]
                    if site_info.can_communicate():
                        self.check_alive_one_url(site_info.url, complete_bans, site_info=site_info)


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
        elif self.args.action == "select":
            self.select()
        elif self.args.action == "split":
            self.split()
            return
        elif self.args.action == "make_redirects":
            self.make_redirects()
        elif self.args.action == "get_title_from_local_files":
            self.get_title_from_local_files()
        elif self.args.action == "check_mirrors":
            self.check_mirrors()
        elif self.args.action == "select_adhoc":
            self.select_adhoc()
        elif self.args.action == "print_web_sites":
            self.print_web_sites()
            return
        else:
            raise Exception("unknown action")

        self.logger.info("write to {}".format(self.args.output_file))
        self.web_sites.offices.write_to_local_file(self.args.output_file)


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()
