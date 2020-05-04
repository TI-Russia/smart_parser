from robots.common.download import  request_url_title,  \
                DEFAULT_HTML_EXTENSION, get_file_extension_by_cached_url
from DeclDocRecognizer.dlrecognizer import DL_RECOGNIZER_ENUM
from collections import defaultdict
from robots.common.http_request import request_url_headers, HttpHeadException
from robots.common.primitives import prepare_for_logging
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from robots.common.find_link import strip_viewer_prefix, click_all_selenium,  \
                    find_links_in_html_by_text, web_link_is_absolutely_prohibited, TLinkInfo
import urllib.error



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
            self.downloaded_files = init_json.get('downloaded_files', list())
            self.dl_recognizer_result = init_json.get('dl_recognizer_result', DL_RECOGNIZER_ENUM.UNKNOWN)
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
            record['downloaded_files'] = self.downloaded_files
        if self.dl_recognizer_result != DL_RECOGNIZER_ENUM.UNKNOWN:
            record['dl_recognizer_result'] = self.dl_recognizer_result
        return record

    def add_downloaded_file(self, record):
        self.downloaded_files.append(record)

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

    def normalize_and_check_link(self, link_info):
        if link_info.TargetUrl is not None:
            link_info.TargetUrl = strip_viewer_prefix(link_info.TargetUrl).strip(" \r\n\t")
            if web_link_is_absolutely_prohibited(link_info.SourceUrl, link_info.TargetUrl):
                return False
        self.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.ElementIndex,
                prepare_for_logging(link_info.TargetUrl), # not redirected yet
                prepare_for_logging(link_info.AnchorText)))
        try:
            return self.step_passport['check_link_func'](link_info)
        except UnicodeEncodeError as exp:
            self.logger.debug(exp)
            return False

    def add_link_wrapper(self, link_info):
        assert link_info.TargetUrl is not None
        try:
            # get rid of http redirects here, for example www.yandex.ru -> yandex.ru to store only one url variant
            # there are also javascript redirects, that can be processed only with a http get request
            # but http get requests are heavy, that's why we deal with them after the link check
            link_info.TargetUrl, _ = request_url_headers(link_info.TargetUrl)
        except UnicodeEncodeError as err:
                return  # unknown exception during urllib.request.urlopen (possibly url has a bad encoding)
        except HttpHeadException as err:
            return # we tried to make http head 3 times, but failed no sense, to retry
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            if isinstance(err, urllib.error.HTTPError)  and err.code == 404:
                return
            pass  # save link and  try one more time to fetch it

        self.website.url_nodes[link_info.SourceUrl].add_child_link(link_info.TargetUrl, link_info.to_json())
        self.step_urls[link_info.TargetUrl] = max(link_info.Weight, self.step_urls[link_info.TargetUrl])
        if link_info.TargetUrl not in self.website.url_nodes:
            if link_info.TargetTitle is None:
                link_info.TargetTitle = request_url_title(link_info.TargetUrl)
            self.website.url_nodes[link_info.TargetUrl] = TUrlInfo(title=link_info.TargetTitle, step_name=self.get_step_name())
        self.website.url_nodes[link_info.TargetUrl].parent_nodes.add(link_info.SourceUrl)
        self.logger.debug("add link {0}".format(link_info.TargetUrl))

    def add_downloaded_file_wrapper(self, link_info):
        self.website.url_nodes[link_info.SourceUrl].add_downloaded_file(link_info.to_json())

    def get_check_func_name(self):
        return self.step_passport['check_link_func'].__name__

    @staticmethod
    def get_url_with_max_weight(d):
        max_v = TLinkInfo.MINIMAL_LINK_WEIGHT - 1.0
        best_k = None
        for k, v in d.items():
            if v >= max_v or best_k is None:
                max_v = v
                best_k = k
        return best_k

    def add_links(self, url, fallback_to_selenium=True):
        file_data, extension = self.website.get_file_data_and_extension(url)
        if extension != DEFAULT_HTML_EXTENSION:
            return
        try:
            soup = BeautifulSoup(file_data, "html.parser")
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
                    self.website.logger.debug('temporal switch on selenium, since this file can be fully javascripted')
                    fallback_to_selenium = True

            if fallback_to_selenium:  # switch off selenium is almost a panic mode (too many links)
                click_all_selenium(self, url, self.website.parent_project.selenium_driver)
        except (urllib.error.HTTPError, urllib.error.URLError, WebDriverException) as e:
            self.websiterlogger.error('add_links failed on url={}, exception: {}'.format(url, e))

    def find_links_for_one_website_transitive(self, start_pages):
        fallback_to_selenium = self.step_passport.get('fallback_to_selenium', True)
        processed_pages = set()
        pages_to_process = defaultdict(float)
        pages_to_process.update(start_pages)
        url_weights = list()
        for url_index in range(TRobotStep.max_step_url_count):
            if len(pages_to_process) == 0:
                break
            url = self.get_url_with_max_weight(pages_to_process)
            url_weight = pages_to_process[url]
            url_weights.append(url_weight)
            # the main robot stop rule
            if url_index > 300 and max(url_weights[-10:]) < 10:
                break

            self.website.logger.debug("max weight={}, index={}, url={} function={}".format(url_weight, url_index,
                                                                                   url,
                                                                                   self.get_check_func_name()))
            processed_pages.add(url)
            del pages_to_process[url]

            self.add_links(url, fallback_to_selenium)

            found_links_count = len(self.step_urls.keys())
            if fallback_to_selenium and found_links_count >= TRobotStep.panic_mode_url_count:
                fallback_to_selenium = False
                self.website.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                    TRobotStep.panic_mode_url_count))
            if self.step_passport.get('transitive', False):
                for u, w in self.step_urls.items():
                    if u not in processed_pages:
                        if get_file_extension_by_cached_url(u) == DEFAULT_HTML_EXTENSION:
                            pages_to_process[u] = max(pages_to_process[u], w)

