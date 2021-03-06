import urllib.parse

from common.download import TDownloadedFile
from common.http_request import THttpRequester
from common.primitives import get_site_domain_wo_www, get_html_title
from common.link_info import TClickEngine
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.web_site_status import TWebSiteReachStatus
from common.export_files import TExportEnvironment
from common.serp_parser import SearchEngine, SerpException

import os
import shutil
import time
import datetime


class TWebSiteCrawlSnapshot:
    SINGLE_DECLARATION_TIMEOUT = 60 * 30 # half an hour in seconds,
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
        self.enable_urllib = True
        self.main_page_url = None
        self.protocol = "http"
        self.web_domain = None
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

    def init_main_page_url_from_redirected_url(self, url):
        o = urllib.parse.urlsplit(url)
        self.protocol = o.scheme
        self.main_page_url = urllib.parse.urlunsplit(
            [o.scheme,
             o.netloc,
             o.path,  # path
             '',  # query
             ''])
        self.web_domain = o.netloc
        assert isinstance(self.web_domain, str)
        if self.web_domain.startswith('www.'):
            self.web_domain = self.web_domain[4:]
        if o.scheme == "https" and self.web_domain.endswith(':443'):
            self.web_domain = self.web_domain[:-4]
        self.logger.debug("main_url_page={}, web_domain={}, protocol={}".format(
            self.main_page_url, self.web_domain, self.protocol))

    def recognize_protocol_and_www(self):
        if self.main_page_url.startswith('http://'):
            self.protocol = "http"
        elif self.main_page_url.startswith('https://'):
            self.protocol = "https"
        else:
            for only_with_www in [False, True]:
                for protocol in ["http", "https"]:
                    try:
                        url = protocol + "://"
                        if only_with_www:
                            url += "www."
                        url += self.main_page_url
                        file = TDownloadedFile(url)
                        html_data = file.data
                        self.logger.debug('read {} bytes from url {}, treat this url as the main url'.format(
                            len(html_data), url))
                        self.init_main_page_url_from_redirected_url(file.redirected_url)
                        return
                    except THttpRequester.RobotHttpException as exp:
                        self.logger.error("cannot fetch {}  with urllib, sleep 3 sec".format(url))
                        time.sleep(3)

    def get_domain_name(self):
        # return example.com (without http)
        assert self.web_domain is not None
        return self.web_domain

    def get_domain_root_page(self):
        # return http://example.com
        assert self.web_domain is not None
        return urllib.parse.urlunsplit((self.protocol, self.web_domain, "", "", ""))

    def init_main_page_default(self, morda_url):
        self.main_page_url = morda_url
        if len(morda_url) > 0:
            if not morda_url.startswith('http'):
                morda_url = 'http://' + morda_url
            o = urllib.parse.urlsplit(morda_url)
            self.web_domain = o.netloc
            self.protocol = o.scheme

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
        self.recognize_protocol_and_www()
        for i in range(3):
            try:
                html_data = TDownloadedFile(self.main_page_url).data
                title = get_html_title(html_data)
                self.reach_status = TWebSiteReachStatus.normal
                self.url_nodes[self.main_page_url] = TUrlInfo(title=title)
                return
            except THttpRequester.RobotHttpException as exp:
                self.logger.error("cannot fetch morda url {} with urllib, sleep 3 sec".format(self.main_page_url))
                time.sleep(3)
        try:
            self.logger.error("disable urllib for this website since we cannot reach the main page with urllib")
            if not self.main_page_url.startswith('http'):
                self.main_page_url = "http://" + self.main_page_url

            self.parent_project.selenium_driver.navigate(self.main_page_url)
            time.sleep(3)
            self.init_main_page_url_from_redirected_url(self.parent_project.selenium_driver.the_driver.current_url)
            title = self.parent_project.selenium_driver.the_driver.title
            self.enable_urllib = False
            self.reach_status = TWebSiteReachStatus.only_selenium
            self.url_nodes[self.main_page_url] = TUrlInfo(title=title)
            return True
        except Exception as exp:
            self.logger.error("cannot access the main page using selenium, exception: {}".format(exp))
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
        self.reach_status = init_json.get('reach_status')
        self.protocol = init_json.get('protocol', "http")
        self.main_page_url = init_json['morda_url']
        self.office_name = init_json.get('name', '')
        self.enable_urllib = init_json.get('enable_urllib', True)
        self.export_env.from_json(init_json.get('exported_files'))
        self.regional_main_pages = init_json.get('regional', list())
        self.web_domain = init_json.get('web_domain')
        if self.web_domain is None:
            self.init_main_page_default(self.main_page_url)

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
            'morda_url': self.main_page_url,
            'web_domain': self.web_domain,
            'regional': self.regional_main_pages,
            'name': self.office_name,
            'enable_urllib': self.enable_urllib,
            'steps': [s.to_json() for s in self.robot_steps],
            'url_nodes': dict( (url, info.to_json()) for url,info in self.url_nodes.items()),
            'exported_files': self.export_env.to_json(),
            'protocol': self.protocol,
        }

    def get_parents(self, url):
        parents = self.url_nodes[url].parent_nodes
        if len(parents) == 0:
            raise Exception("cannot find parent for {}".format(url))
        for p in parents:
            yield p

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
        return os.path.join(self.parent_project.export_folder, self.get_domain_name()).replace(':', '_')

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


