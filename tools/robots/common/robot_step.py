from robots.common.download import TDownloadedFile, DEFAULT_HTML_EXTENSION
from DeclDocRecognizer.dlrecognizer import DL_RECOGNIZER_ENUM
from collections import defaultdict
from robots.common.primitives import prepare_for_logging, strip_viewer_prefix
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from robots.common.find_link import click_all_selenium,  find_links_in_html_by_text, \
                    web_link_is_absolutely_prohibited
from robots.common.link_info import TLinkInfo
from robots.common.primitives import get_html_title
from robots.common.http_request import RobotHttpException


class TUrlMirror:
    def __init__(self, url):
        self.input_url  = url
        self.protocol_prefix = ''
        self.www_prefix = ''
        for prefix in ['http://', 'https://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                self.protocol_prefix = prefix
                break
        for prefix in ['www']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                self.www_prefix = prefix
        self.normalized_url = url


class TUrlInfo:
    def __init__(self, title=None, step_name=None, init_json=None):
        if init_json is not None:
            self.step_name = init_json['step']
            self.title = init_json['title']
            self.parent_nodes = set(init_json.get('parents', list()))
            self.linked_nodes = init_json.get('links', dict())
            self.dl_recognizer_result = init_json.get('dl_recognizer_result', DL_RECOGNIZER_ENUM.UNKNOWN)
            self.downloaded_files = list()
            for rec in init_json.get('downloaded_files', list()):
                self.downloaded_files.append(TLinkInfo(None, None, None).from_json(rec))
        else:
            self.step_name = step_name
            self.title = title
            self.parent_nodes = set()
            self.linked_nodes = dict()
            self.downloaded_files = list()
            self.dl_recognizer_result = DL_RECOGNIZER_ENUM.UNKNOWN

    def to_json(self):
        record = {
            'step': self.step_name,
            'title': self.title,
            'parents': list(self.parent_nodes),
            'links': self.linked_nodes,
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = list(x.to_json() for x in self.downloaded_files)
        if self.dl_recognizer_result != DL_RECOGNIZER_ENUM.UNKNOWN:
            record['dl_recognizer_result'] = self.dl_recognizer_result
        return record

    def add_downloaded_file(self, link_info: TLinkInfo):
        self.downloaded_files.append(link_info)

    def add_child_link(self, href, record):
        self.linked_nodes[href] = record


class TRobotStep:
    panic_mode_url_count = 600
    max_step_url_count = 800

    def __init__(self, website, step_passport, init_json=None):
        self.website = website
        self.logger = website.logger
        self.step_passport = step_passport
        self.profiler = dict()
        self.step_urls = defaultdict(float)
        # runtime members
        self.processed_pages = None
        self.pages_to_process = dict()
        self.url_weights = None

        if init_json is not None:
            step_urls = init_json.get('step_urls')
            if isinstance(step_urls, list):
                self.step_urls.update(dict((k, TLinkInfo.MINIMAL_LINK_WEIGHT) for k in step_urls))
            else:
                assert (isinstance(step_urls, dict))
                self.step_urls.update(step_urls)
            self.profiler = init_json.get('profiler', dict())

    def get_step_name(self):
        return self.step_passport['step_name']

    def is_last_step(self):
        return self.get_step_name() == self.website.parent_project.robot_step_passports[-1]['step_name']

    def delete_url_mirrors_by_www_and_protocol_prefix(self):
        mirrors = defaultdict(list)
        for u in self.step_urls:
            m = TUrlMirror(u)
            mirrors[m.normalized_url].append(m)
        new_step_urls = defaultdict(float)
        for urls in mirrors.values():
            urls = sorted(urls, key=(lambda x: len(x.input_url)))
            max_weight = max(self.step_urls[u] for u in urls)
            new_step_urls[urls[-1].input_url] = max_weight  # get the longest url and max weight
        self.step_urls = new_step_urls

    def to_json(self):
        return {
            'step_name': self.get_step_name(),
            'step_urls': dict( (k,v) for (k, v)  in self.step_urls.items() ),
            'profiler': self.profiler
        }

    def normalize_and_check_link(self, link_info: TLinkInfo):
        if link_info.target_url is not None:
            link_info.target_url = strip_viewer_prefix(link_info.target_url).strip(" \r\n\t")
            if web_link_is_absolutely_prohibited(link_info.source_url, link_info.target_url):
                return False
        self.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.element_index,
                prepare_for_logging(link_info.target_url), # not redirected yet
                prepare_for_logging(link_info.anchor_text)))
        try:
            return self.step_passport['check_link_func'](link_info)
        except UnicodeEncodeError as exp:
            self.logger.debug(exp)
            return False

    def add_link_wrapper(self, link_info: TLinkInfo):
        assert link_info.target_url is not None
        try:
            downloaded_file = TDownloadedFile(link_info.target_url)
        except RobotHttpException as err:
            self.logger.error(err)
            return

        href = link_info.target_url

        self.website.url_nodes[link_info.source_url].add_child_link(href, link_info.to_json())
        link_info.weight = max(link_info.weight, self.step_urls[href])
        self.step_urls[href] = link_info.weight

        if href not in self.website.url_nodes:
            if link_info.target_title is None and downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                link_info.target_title = get_html_title(downloaded_file.data)
            self.website.url_nodes[href] = TUrlInfo(title=link_info.target_title, step_name=self.get_step_name())

        self.website.url_nodes[href].parent_nodes.add(link_info.source_url)

        if self.is_last_step():
            self.website.export_env.export_file(downloaded_file, self.website.url_nodes[href])

        if self.step_passport.get('transitive', False):
            if href not in self.processed_pages:
                if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                    self.pages_to_process[href] = link_info.weight

        self.logger.debug("add link {0}".format(href))

    def add_downloaded_file_wrapper(self, link_info: TLinkInfo):
        self.website.url_nodes[link_info.source_url].add_downloaded_file(link_info)
        if self.is_last_step():
            self.website.export_env.export_selenium_doc(link_info)

    def get_check_func_name(self):
        return self.step_passport['check_link_func'].__name__

    def add_page_links(self, url, fallback_to_selenium=True):
        try:
            downloaded_file = TDownloadedFile(url)
        except RobotHttpException as err:
            self.logger.error(err)
            return
        if downloaded_file.file_extension != DEFAULT_HTML_EXTENSION:
            return
        try:
            soup = BeautifulSoup(downloaded_file.data, "html.parser")
        except Exception as e:
            self.logger.error('cannot parse html, exception {}'.format(url, e))
            return
        already_processed = self.website.find_a_web_page_with_a_similar_html(self, url, soup)
        try:
            if already_processed is None:
                find_links_in_html_by_text(self, url, soup)
            else:
                self.logger.error(
                    'skip processing {} in find_links_in_html_by_text, a similar file is already processed on this step: {}'.format(url, already_processed))

                if not fallback_to_selenium and len(list(soup.findAll('a'))) < 10:
                    self.logger.debug('temporal switch on selenium, since this file can be fully javascripted')
                    fallback_to_selenium = True

            if fallback_to_selenium:  # switch off selenium is almost a panic mode (too many links)
                if downloaded_file.get_file_extension_only_by_headers() != DEFAULT_HTML_EXTENSION:
                    # selenium reads only http headers, so downloaded_file.file_extension can be DEFAULT_HTML_EXTENSION
                    self.logger.debug("do not browse {} with selenium, since it has wrong http headers".format(url))
                else:
                    click_all_selenium(self, url, self.website.parent_project.selenium_driver)
        except (RobotHttpException, WebDriverException) as e:
            self.logger.error('add_links failed on url={}, exception: {}'.format(url, e))

    def pop_url_with_max_weight(self, url_index):
        if len(self.pages_to_process) == 0:
            return None
        if url_index > 100:
            if url_index > 200 or max(self.url_weights[-10:]) < TLinkInfo.NORMAL_LINK_WEIGHT:
                if self.website.export_env.waiting_too_long():
                    self.website.logger.error("stop crawling since last time no declaration found")
                    return None
        max_weight = TLinkInfo.MINIMAL_LINK_WEIGHT - 1.0
        best_url = None
        for url, weight in self.pages_to_process.items():
            if weight >= max_weight or best_url is None:
                max_weight = weight
                best_url = url
        if best_url is None:
            return None
        self.processed_pages.add(best_url)
        del self.pages_to_process[best_url]
        self.url_weights.append(max_weight)
        self.website.logger.debug("max weight={}, index={}, url={} function={}".format(max_weight, url_index,
                                                                                       best_url,
                                                                                       self.get_check_func_name()))
        return best_url

    def make_one_step(self):
        assert len(self.pages_to_process) > 0
        self.url_weights = list()
        fallback_to_selenium = self.step_passport.get('fallback_to_selenium', True)
        for url_index in range(TRobotStep.max_step_url_count):
            url = self.pop_url_with_max_weight(url_index)
            if url is None:
                break

            self.add_page_links(url, fallback_to_selenium)

            if fallback_to_selenium and len(self.step_urls.keys()) >= TRobotStep.panic_mode_url_count:
                fallback_to_selenium = False
                self.website.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                    TRobotStep.panic_mode_url_count))


