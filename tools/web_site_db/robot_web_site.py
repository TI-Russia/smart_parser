from common.http_request import THttpRequester
from common.link_info import TClickEngine
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.web_site_status import TWebSiteReachStatus
from common.export_files import TExportEnvironment
from common.serp_parser import SearchEngine, SerpException
import common.urllib_parse_pro as urllib_parse_pro
from common.urllib_parse_pro import strip_scheme_and_query, site_url_to_file_name
from selenium.common.exceptions import WebDriverException

import os
import shutil
import time
import datetime
import urllib.parse


class TWebSiteCrawlSnapshot:
    DEFAULT_CRAWLING_TIMEOUT = 60 * 60 * 3 # 3 hours
    CRAWLING_TIMEOUT = DEFAULT_CRAWLING_TIMEOUT

    def __init__(self, project, morda_url=""):
        #runtime members (no serialization)
        self.start_crawling_time = time.time()
        self.parent_project = project
        self.logger = project.logger
        self.export_env = TExportEnvironment(self)
        self.stopped_by_timeout = False

        #serialized members
        self.url_nodes = dict()
        self.main_page_url = None
        self.input_site_url = None
        self.office_name = ""
        self.reach_status = TWebSiteReachStatus.normal
        self.regional_main_pages = list()
        self.reach_status = None
        self.init_main_page_default(morda_url)
        self.other_projects_regexp = self.parent_project.web_sites_db.get_other_sites_regexp_on_the_same_web_domain(morda_url)

        self.robot_steps = list()
        for i in range(len(project.robot_step_passports)):
            is_last_step = (i == len(project.robot_step_passports) - 1)
            passport = project.robot_step_passports[i]
            step = TRobotStep(self, **passport, is_last_step=is_last_step)
            self.robot_steps.append(step)

    # declarations number per minute
    def get_robot_speed(self):
        elapsed_time_in_seconds = time.time() - self.start_crawling_time + 0.00000001
        return (60.0 * self.export_env.found_declarations_count) / elapsed_time_in_seconds;

    def url_is_not_linked_to_another_project(self, url):
        if self.other_projects_regexp is None:
            return True
        return self.other_projects_regexp.search(url) is None

    def init_main_page_url_from_redirected_url(self, url, title):
        o = urllib_parse_pro.urlsplit_pro(url)
        netloc = o.netloc
        scheme = o.scheme
        if scheme == 'http' and netloc.endswith(':443'):
            self.logger.debug("coerce url {} to https".format(url))
            netloc = netloc[0:-len(':443')]
            scheme = 'https'
        self.main_page_url = urllib.parse.urlunsplit(
            [scheme,
             netloc,
             o.path,  # path
             '',  # query
             ''])
        self.logger.debug("main_url_page={}".format(self.main_page_url))
        self.reach_status = TWebSiteReachStatus.normal
        self.url_nodes[self.main_page_url] = TUrlInfo(title=title)

    def get_url_modifications(url: str):
        o = urllib_parse_pro.urlsplit_pro(url)
        if len(o.scheme) > 0:
            protocols = [o.scheme]
        else:
            protocols = ["http", "https"]
        if o.netloc.startswith("www."):
            with_www = [True]
        else:
            with_www = [True, False]
        for only_with_www in with_www:
            for protocol in protocols:
                host = o.netloc
                if only_with_www:
                    host = "www." + host
                modified_url = urllib.parse.urlunsplit((protocol, host, o.path, o.query, o.fragment))
                yield modified_url

    def recognize_protocol_and_www_selenium(self):
        for url in urllib_parse_pro.get_url_modifications(self.input_site_url):
            try:
                self.parent_project.selenium_driver.navigate(url)
                time.sleep(3)
                title = self.parent_project.selenium_driver.the_driver.title
                self.init_main_page_url_from_redirected_url(
                    self.parent_project.selenium_driver.the_driver.current_url,
                    title)
                return
            except WebDriverException as exp:
                self.logger.error("cannot fetch {}  with selenium, sleep 3 sec".format(url))
                time.sleep(3)
        raise THttpRequester.RobotHttpException(
            "there is no way to access {}".format(self.input_site_url),
            self.input_site_url,
            404,
            "GET")

    def get_site_url(self):
        # 1. in many cases this function returns the web domain, sometimes it can return the web domain and url path
        # like "mos.ru/dpi"
        # 2. self.get_site_url() can differ from self.input_site_url, if there is a new http-redirection
        return strip_scheme_and_query(self.main_page_url)

    def get_main_url_protocol(self):
        return str(urllib_parse_pro.urlsplit_pro(self.main_page_url).scheme)

    def init_main_page_default(self, morda_url):
        self.input_site_url = morda_url
        self.main_page_url = morda_url

    def fetch_the_main_page(self, enable_search_engine=True):
        if len(self.url_nodes) > 0:
            return True
        try:
            self.recognize_protocol_and_www_selenium()
            return True
        except THttpRequester.RobotHttpException as exp:
            self.reach_status = TWebSiteReachStatus.out_of_reach

        if enable_search_engine:
            try:
                urls = SearchEngine().site_search(0, self.main_page_url, "", self.parent_project.selenium_driver)
                if len(urls) == 0:
                    self.reach_status = TWebSiteReachStatus.abandoned
            except SerpException as exp:
                self.logger.error("cannot find this page using search engine")
                self.reach_status = TWebSiteReachStatus.abandoned

        return False

    def check_crawling_timeouts(self, robot_speed, crawled_web_pages_count):
        current_time = time.time()
        crawl_time_all_steps = current_time - self.start_crawling_time
        if crawl_time_all_steps > TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT:
            self.logger.error("timeout stop crawling: TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT={}".format(TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT))
            self.stopped_by_timeout = True
            return False

        if crawl_time_all_steps < 1 * 60 * 60:
            max_next_declaration_timeout = 1 * 60 * 60  # 1 hour
        elif crawl_time_all_steps < 5 * 60 * 60:
            max_next_declaration_timeout = 30 * 60  # 30 minutes
        else:
            max_next_declaration_timeout = 15 * 60  # 15 minutes
        is_low_robot_speed = (robot_speed < 1.0 and crawled_web_pages_count > 100)
        too_much_time_for_one_site = crawl_time_all_steps > 60 * 60 * 3
        last_declaration_was_long_ago = (current_time - self.export_env.last_found_declaration_time > max_next_declaration_timeout)
        if (is_low_robot_speed or too_much_time_for_one_site) and last_declaration_was_long_ago:
            self.logger.error("timeout stop crawling: last_declaration_timeout={} robot_speed={}".format(
                max_next_declaration_timeout, robot_speed))
            self.stopped_by_timeout = True
            return False
        return True

    def read_from_json(self, init_json):
        self.input_site_url = init_json.get('morda_url')
        self.reach_status = init_json.get('reach_status')
        self.main_page_url = init_json.get('main_page_url', init_json.get('morda_url'))
        self.office_name = init_json.get('name', '')
        self.export_env.from_json(init_json.get('exported_files'))
        self.regional_main_pages = init_json.get('regional', list())

        if init_json.get('steps') is not None:
            self.robot_steps = list()
            steps = init_json.get('steps', list())
            for i in range(len(steps)):
                step = self.parent_project.robot_step_passports[i]
                self.robot_steps.append(TRobotStep(self, **step, is_last_step=(i == len(steps) - 1)))
        for url, info in init_json.get('url_nodes', dict()).items():
            self.url_nodes[url] = TUrlInfo().from_json(info)
        return self

    def to_json(self):
        return {
            'reach_status': self.reach_status,
            'main_page_url': self.main_page_url,
            'morda_url': self.input_site_url,
            'regional': self.regional_main_pages,
            'name': self.office_name,
            'steps': [s.to_json() for s in self.robot_steps],
            'url_nodes': dict( (url, info.to_json()) for url,info in self.url_nodes.items()),
            'exported_files': self.export_env.to_json(),
        }

    def get_regional_pages(self):
        # not used now (was used for genproc.gov.ru)
        for url in self.regional_main_pages:
            if not url.startswith('http'):
                url = self.get_main_url_protocol() + "://" + url
            yield url

    def get_parents(self, url):
        parents = self.url_nodes[url].parent_nodes
        if len(parents) == 0:
            raise Exception("cannot find parent for {}".format(url))
        for p in parents:
            yield p

    def get_title(self, url):
        info: TUrlInfo
        info = self.url_nodes[url]
        return info.html_title

    def get_path_to_root_recursive(self, path, all_paths, max_path_len=40):
        assert len(path) >= 1
        assert type(all_paths) is list
        top_node = path[-1]
        top_url = top_node['source:url']
        if top_url == self.main_page_url:
            all_paths.append(list(path))
            return
        if len(path) > max_path_len:
            return
        start = datetime.datetime.now()
        for parent_url in self.get_parents(top_url):
            if parent_url in (u['source:url'] for u in path):  # prevent cycles:
                continue
            parent_url_info = self.url_nodes[parent_url]
            link_info = parent_url_info.linked_nodes[top_url]
            engine = link_info.get('engine', '')
            if TClickEngine.is_search_engine(engine):
                record = {
                    'search_query': link_info['text'],
                }
                all_paths.append(list(path) + [record])
            else:
                record = {
                    'source:url': parent_url,
                    'source:step': parent_url_info.step_name,
                    'source:title': parent_url_info.html_title,
                    'target:anchor_text': link_info['text'],
                    'target:engine': engine
                }
                self.get_path_to_root_recursive(list(path) + [record], all_paths)
            if (datetime.datetime.now() - start).total_seconds() > 2:
                break

    def get_shortest_path_to_root(self, url):
        def get_joined_path(path):
            return " ".join(u.get('source:url', '') for u in path)
        url_info = self.url_nodes[url]
        record = {'source:url': url, 'step': url_info.step_name}
        path = [record]
        all_paths = list()
        self.get_path_to_root_recursive(path, all_paths)
        if len(all_paths) == 0:
            return [{"exception": "graph is too large, timeout is set to 2 seconds"}]
        if len(all_paths) > 5000:
            return [{"exception": "graph is too large, too many paths (>5000)"}]
        all_paths = sorted(all_paths, key=get_joined_path)
        path_lens = list(len(p) for p in all_paths)
        min_path = all_paths[path_lens.index(min(path_lens))]
        min_path.reverse()
        return min_path

    def get_export_folder(self):
        folder = site_url_to_file_name(self.get_site_url())
        return os.path.join(self.parent_project.export_folder, folder)

    def create_export_folder(self):
        office_folder = self.get_export_folder()
        if os.path.exists(office_folder):
            shutil.rmtree(office_folder)
        os.makedirs(office_folder)

    def find_links_for_one_website(self, step_index: int):
        if not TWebSiteReachStatus.can_communicate(self.reach_status):
            return

        if step_index == 0:
            previous_step_urls = {self.main_page_url: 0}
        else:
            previous_step_urls = self.robot_steps[step_index - 1].url_to_weight

        self.robot_steps[step_index].make_one_step(previous_step_urls)


