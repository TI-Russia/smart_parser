from common.download import TDownloadedFile
from common.http_request import THttpRequester
from common.html_parser import get_html_title
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
    SINGLE_DECLARATION_TIMEOUT = 60 * 30 # half an hour in seconds,
    DEFAULT_CRAWLING_TIMEOUT = 60 * 60 * 3 # 3 hours
    CRAWLING_TIMEOUT = DEFAULT_CRAWLING_TIMEOUT

    @staticmethod
    def default_enable_urllib():
        s = os.environ.get('DLROBOT_ENABLE_URLLIB', "0")
        return s == "True" or s == "1"

    def __init__(self, project, morda_url=""):
        #runtime members (no serialization)
        self.start_crawling_time = time.time()
        self.parent_project = project
        self.logger = project.logger
        self.export_env = TExportEnvironment(self)
        self.stopped_by_timeout = False

        #serialized members
        self.url_nodes = dict()
        self.enable_urllib = self.default_enable_urllib()
        self.main_page_url = None
        self.input_site_url = None
        self.office_name = ""
        self.reach_status = TWebSiteReachStatus.normal
        self.regional_main_pages = list()
        self.reach_status = None
        self.init_main_page_default(morda_url)

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

    def recognize_protocol_and_www(self):
        for url in urllib_parse_pro.get_url_modifications(self.input_site_url):
            try:
                file = TDownloadedFile(url)
                title = get_html_title(file.data)
                self.init_main_page_url_from_redirected_url(file.redirected_url, title)
                return
            except THttpRequester.RobotHttpException as exp:
                self.logger.error("cannot fetch {}  with urllib, sleep 3 sec".format(url))
                time.sleep(3)

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

    def check_urllib_access(self):
        if self.enable_urllib:
            if not THttpRequester.check_urllib_access_with_many_head_requests(self.main_page_url):
                self.logger.info("disable urllib, since there are too many timeouts to head requests")
                self.enable_urllib = False
                if not self.parent_project.enable_selenium:
                    self.parent_project.reenable_selenium()

    def fetch_the_main_page(self, enable_search_engine=True):
        if len(self.url_nodes) > 0:
            return True
        if self.enable_urllib:
            try:
                self.recognize_protocol_and_www()
                return True
            except THttpRequester.RobotHttpException as exp:
                self.logger.error("disable urllib for this website since we cannot reach the main page with urllib")
                self.enable_urllib = False

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

    def check_crawling_timeouts(self, enough_crawled_urls):
        current_time = time.time()
        if enough_crawled_urls and current_time - self.export_env.last_found_declaration_time > TWebSiteCrawlSnapshot.SINGLE_DECLARATION_TIMEOUT:
            self.logger.error("timeout stop crawling: TWebSiteCrawlSnapshot.SINGLE_DECLARATION_TIMEOUT")
            self.stopped_by_timeout = True
            return False
        if current_time - self.start_crawling_time > TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT:
            self.logger.error("timeout stop crawling: TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT")
            self.stopped_by_timeout = True
            return False
        return True

    def read_from_json(self, init_json):
        self.input_site_url = init_json.get('morda_url')
        self.reach_status = init_json.get('reach_status')
        self.main_page_url = init_json.get('main_page_url', init_json.get('morda_url'))
        self.office_name = init_json.get('name', '')
        self.enable_urllib = init_json.get('enable_urllib', self.default_enable_urllib())
        self.export_env.from_json(init_json.get('exported_files'))
        self.regional_main_pages = init_json.get('regional', list())

        if init_json.get('steps') is not None:
            self.robot_steps = list()
            steps = init_json.get('steps', list())
            for i in range(len(steps)):
                step = self.parent_project.robot_step_passports[i]
                self.robot_steps.append(TRobotStep(self, **step, is_last_step=(i == len(steps) - 1)))
        for url, info in init_json.get('url_nodes', dict()).items():
            self.url_nodes[url] = TUrlInfo(init_json=info)
        return self

    def to_json(self):
        return {
            'reach_status': self.reach_status,
            'main_page_url': self.main_page_url,
            'morda_url': self.input_site_url,
            'regional': self.regional_main_pages,
            'name': self.office_name,
            'enable_urllib': self.enable_urllib,
            'steps': [s.to_json() for s in self.robot_steps],
            'url_nodes': dict( (url, info.to_json()) for url,info in self.url_nodes.items()),
            'exported_files': self.export_env.to_json(),
        }

    def get_parents(self, url):
        parents = self.url_nodes[url].parent_nodes
        if len(parents) == 0:
            raise Exception("cannot find parent for {}".format(url))
        for p in parents:
            yield p

    def get_title(self, url):
        info: TUrlInfo
        info = self.url_nodes[url]
        return info.title

    def get_path_to_root_recursive(self, path, all_paths):
        assert len(path) >= 1
        assert type(all_paths) is list
        top_node = path[-1]
        top_url = top_node['source:url']
        if top_url == self.main_page_url:
            all_paths.append(list(path))
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
                    'source:title': parent_url_info.title,
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
            previous_step_urls = self.robot_steps[step_index - 1].step_urls

        self.robot_steps[step_index].make_one_step(previous_step_urls, self.regional_main_pages)


