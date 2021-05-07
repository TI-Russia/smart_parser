from common.download import TDownloadedFile
from common.http_request import THttpRequester
from collections import defaultdict
from common.primitives import get_site_domain_wo_www, get_html_title
import os
import shutil
import time
import datetime
import hashlib
import re
from common.link_info import TLinkInfo, TClickEngine
from web_site_db.robot_step import TRobotStep, TUrlInfo
from common.export_files import TExportEnvironment
from common.serp_parser import SearchEngine, SerpException

from usp.tree import sitemap_tree_for_homepage

#disable logging for usp.tree
import logging
for name in logging.root.manager.loggerDict:
    if name.startswith('usp.'):
        logging.getLogger(name).setLevel(logging.CRITICAL)


class TWebSiteReachStatus:
    normal = "normal"
    only_selenium = "only_selenium"
    out_of_reach = "out_of_reach"   #nor urllib, neither selenium
    out_of_reach2 = "out_of_reach2" #we got out_of_reach at least two times
    abandoned = "abandoned"         #no trace in search engines

    @staticmethod
    def can_communicate(reach_status):
        return reach_status == TWebSiteReachStatus.normal or \
               reach_status == TWebSiteReachStatus.only_selenium

    @staticmethod
    def check_status(status):
        return status in {TWebSiteReachStatus.normal, TWebSiteReachStatus.only_selenium,
                           TWebSiteReachStatus.out_of_reach, TWebSiteReachStatus.abandoned,
                          TWebSiteReachStatus.out_of_reach2}


class TWebSiteCrawlSnapshot:
    SINGLE_DECLARATION_TIMEOUT = 60 * 30 # half an hour in seconds,
    DEFAULT_CRAWLING_TIMEOUT = 60 * 60 * 3 # 3 hours
    CRAWLING_TIMEOUT = DEFAULT_CRAWLING_TIMEOUT

    def __init__(self, project):
        #runtime members (no serialization)
        self.start_crawling_time = time.time()
        self.parent_project = project
        self.logger = project.logger
        self.runtime_processed_files = dict()
        self.export_env = TExportEnvironment(self)
        self.stopped_by_timeout = False

        #serialized members
        self.url_nodes = dict()
        self.enable_urllib = True
        self.morda_url = ""
        self.office_name = ""
        self.reach_status = TWebSiteReachStatus.normal
        self.robot_steps = list()
        self.regional_main_pages = list()
        self.reach_status = None
        self.protocol = "http"
        self.only_with_www = False

        if len(self.robot_steps) == 0:
            for p in project.robot_step_passports:
                self.robot_steps.append(TRobotStep(self, p))
        assert len(self.robot_steps) == len(project.robot_step_passports)

    def recognize_protocol_and_www(self):
        if self.morda_url.startswith('http://'):
            self.protocol = "http"
        elif self.morda_url.startswith('https://'):
            self.protocol = "https"
        else:
            for only_with_www in [False, True]:
                for protocol in ["http", "https"]:
                    try:
                        url = protocol + "://"
                        if only_with_www:
                            url += "www."
                        url += self.morda_url
                        html_data = TDownloadedFile(url).data
                        self.morda_url = url
                        self.logger.debug('set main url to {}'.format(url))
                        self.protocol = protocol
                        self.only_with_www = only_with_www
                        return
                    except THttpRequester.RobotHttpException as exp:
                        self.logger.error("cannot fetch {}  with urllib, sleep 3 sec".format(url))
                        time.sleep(3)

    def get_domain_name(self):
        return get_site_domain_wo_www(self.morda_url)

    def fetch_the_main_page(self):
        if len(self.url_nodes) > 0:
            return True
        self.recognize_protocol_and_www()
        for i in range(3):
            try:
                html_data = TDownloadedFile(self.morda_url).data
                title = get_html_title(html_data)
                self.reach_status = TWebSiteReachStatus.normal
                self.url_nodes[self.morda_url] = TUrlInfo(title=title)
                return
            except THttpRequester.RobotHttpException as exp:
                self.logger.error("cannot fetch morda url {} with urllib, sleep 3 sec".format(self.morda_url))
                time.sleep(3)
        try:
            self.logger.error("disable urllib for this website since we cannot reach the main page with urllib")
            self.parent_project.selenium_driver.navigate(self.morda_url)
            time.sleep(3)
            title = self.parent_project.selenium_driver.the_driver.title
            self.enable_urllib = False
            self.reach_status = TWebSiteReachStatus.only_selenium
            self.url_nodes[self.morda_url] = TUrlInfo(title=title)
            return True
        except Exception as exp:
            self.logger.error ("cannot access the main page using selenium")
            self.reach_status = TWebSiteReachStatus.out_of_reach

        try:
            urls = SearchEngine().site_search(0, get_site_domain_wo_www(self.morda_url), "", self.parent_project.selenium_driver)
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
        self.only_with_www = init_json.get('only_with_www')
        self.protocol = init_json.get('protocol', "http")
        self.morda_url = init_json['morda_url']
        self.office_name = init_json.get('name', '')
        self.enable_urllib = init_json.get('enable_urllib', True)
        self.export_env.from_json(init_json.get('exported_files'))
        self.regional_main_pages = init_json.get('regional', list())

        if init_json.get('steps') is not None:
            self.robot_steps = list()
            for step_no, step in enumerate(init_json.get('steps', list())):
                self.robot_steps.append(TRobotStep(self, self.parent_project.robot_step_passports[step_no], init_json=step))
        for url, info in init_json.get('url_nodes', dict()).items():
            self.url_nodes[url] = TUrlInfo(init_json=info)
        return self

    def to_json(self):
        return {
            'reach_status': self.reach_status,
            'morda_url': self.morda_url,
            'regional': self.regional_main_pages,
            'name': self.office_name,
            'enable_urllib': self.enable_urllib,
            'steps': [s.to_json() for s in self.robot_steps],
            'url_nodes': dict( (url, info.to_json()) for url,info in self.url_nodes.items()),
            'exported_files': self.export_env.to_json(),
            'protocol': self.protocol,
            'only_with_www': self.only_with_www
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
        if top_url == self.morda_url:
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

    def find_a_web_page_with_a_similar_html(self, step_info: TRobotStep, url, html_text):
        if len(html_text) > 1000:
            html_text = re.sub('[0-9]+', 'd', html_text)
            hash_code = "{}_{}_{}".format(step_info.get_step_name(), step_info.get_check_func_name(),
                                       hashlib.sha256(html_text.encode("utf8")).hexdigest())
            already = self.runtime_processed_files.get(hash_code)
            if already is not None:
                return already
            self.runtime_processed_files[hash_code] = url
        return None

    def get_previous_step_urls(self, step_index):
        if step_index == 0:
            rec = {self.morda_url: 0}
            return rec
        else:
            return self.robot_steps[step_index - 1].step_urls

    def add_regional_main_pages(self, target: TRobotStep):
        for url in self.regional_main_pages:
            if not url.startswith('http'):
                url = self.protocol + "://" + url
            link_info = TLinkInfo(TClickEngine.manual, self.morda_url, url)
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            target.add_link_wrapper(link_info)

    def add_links_from_sitemap_xml(self, check_url_func, step_info: TRobotStep):
        tree = sitemap_tree_for_homepage(self.morda_url)
        cnt = 0
        useful = 0
        for page in tree.all_pages():
            cnt += 1
            weight = check_url_func(page.url)
            if weight > TLinkInfo.MINIMAL_LINK_WEIGHT:
                if page.url not in step_info.pages_to_process:
                    useful += 1
                    link_info = TLinkInfo(TClickEngine.sitemap_xml, self.morda_url, page.url, anchor_text="")
                    link_info.weight = weight
                    step_info.add_link_wrapper(link_info)
        self.logger.info("processed {} links from sitemap.xml found {} useful links".format(cnt, useful))

    def find_links_for_one_website(self, step_index: int):
        if not TWebSiteReachStatus.can_communicate(self.reach_status):
            return
        step_passport = self.parent_project.robot_step_passports[step_index]
        step_name = step_passport['step_name']
        self.logger.info("=== step {0} =========".format(step_name))
        self.logger.info(self.get_domain_name())
        include_source = step_passport['include_sources']
        is_last_step = step_index == len(self.parent_project.robot_step_passports) - 1
        target = self.robot_steps[step_index]
        target.step_urls = defaultdict(float)
        start_time = time.time()
        if is_last_step:
            self.create_export_folder()

        start_pages = self.get_previous_step_urls(step_index)

        target.pages_to_process = dict(start_pages)
        target.processed_pages = set()

        if include_source == "always":
            assert not is_last_step  # todo: should we export it?
            target.step_urls.update(target.pages_to_process)

        if self.parent_project.need_search_engine_before(target):
            self.parent_project.use_search_engine(target)
            target.pages_to_process.update(target.step_urls)

        if step_passport.get('sitemap_xml'):
            self.add_links_from_sitemap_xml(step_passport.get('sitemap_xml', {}).get('check_url_func'), target)

        save_input_urls = dict(target.pages_to_process.items())

        target.apply_function_to_links(step_passport['check_link_func'])

        if len(target.step_urls) == 0:
            func2 = step_passport.get('check_link_func_2')
            if func2:
                self.logger.debug("second pass with {}".format(func2.__name__))
                target.pages_to_process = save_input_urls
                target.apply_function_to_links(func2)

        if self.parent_project.need_search_engine_after(target):
            self.parent_project.use_search_engine(target)

        if step_index == 0:
            self.add_regional_main_pages(target)

        if include_source == "copy_if_empty" and len(target.step_urls) == 0:
            do_not_copy_urls_from_steps = step_passport.get('do_not_copy_urls_from_steps', list())
            for url, weight in start_pages.items():
                step_name = self.url_nodes[url].step_name
                if step_name not in do_not_copy_urls_from_steps:
                    target.step_urls[url] = weight

        target.profiler = {
            "elapsed_time":  time.time() - start_time,
            "step_request_rate": THttpRequester.get_request_rate(start_time),
            "site_request_rate": THttpRequester.get_request_rate()
        }
        self.logger.debug("{}".format(str(target.profiler)))
        target.delete_url_mirrors_by_www_and_protocol_prefix()
        self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(target.step_urls)))

