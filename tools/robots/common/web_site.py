from robots.common.download import get_local_file_name_by_url, request_url_title, read_from_cache_or_download,  \
                DEFAULT_HTML_EXTENSION, get_file_extension_by_cached_url,  convert_html_to_utf8
from DeclDocRecognizer.dlrecognizer import DL_RECOGNIZER_ENUM
from collections import defaultdict
from robots.common.primitives import get_site_domain_wo_www
import os
import shutil
import time
import datetime
from robots.common.http_request import request_url_headers, get_request_rate, HttpHeadException
from robots.common.primitives import prepare_for_logging
import hashlib
import re
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from robots.common.find_link import strip_viewer_prefix, click_all_selenium,  \
                    find_links_in_html_by_text, web_link_is_absolutely_prohibited, TLinkInfo, TClickEngine
import urllib.error


FIXLIST = {
    'fsin.su': {
        "anticorruption_div" : "http://www.fsin.su/anticorrup2014/"
    },
    'fso.gov.ru': {
        "anticorruption_div" : "http://www.fso.gov.ru/korrup.html"
    }
}


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
    def __init__(self, step_name, init_json=None):
        self.step_name = step_name
        self.profiler = dict()
        self.step_urls = defaultdict(float)
        if init_json  is not None:
            step_urls = init_json.get('step_urls')
            if isinstance(step_urls, list):
                self.step_urls.update(dict((k, TLinkInfo.MINIMAL_LINK_WEIGHT) for k in step_urls))
            else:
                assert (isinstance(step_urls, dict))
                self.step_urls.update(step_urls)
            self.profiler = init_json.get('profiler', dict())

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
            'step_name': self.step_name,
            'step_urls': dict( (k,v) for (k, v)  in self.step_urls.items() ),
            'profiler': self.profiler
        }


class TProcessUrlTemporary:
    def __init__(self, website, robot_step, step_passport):
        self.website = website
        self.robot_step = robot_step
        self.step_passport = step_passport

    def normalize_and_check_link(self, link_info):
        if link_info.TargetUrl is not None:
            link_info.TargetUrl = strip_viewer_prefix(link_info.TargetUrl).strip(" \r\n\t")
            if web_link_is_absolutely_prohibited(link_info.SourceUrl, link_info.TargetUrl):
                return False
        self.website.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.ElementIndex,
                prepare_for_logging(link_info.TargetUrl), # not redirected yet
                prepare_for_logging(link_info.AnchorText)))
        try:
            return self.step_passport['check_link_func'](link_info)
        except UnicodeEncodeError as exp:
            self.website.logger.debug(exp)
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
        self.robot_step.step_urls[link_info.TargetUrl] = max(link_info.Weight, self.robot_step.step_urls[link_info.TargetUrl])
        if link_info.TargetUrl not in self.website.url_nodes:
            if link_info.TargetTitle is None:
                link_info.TargetTitle = request_url_title(link_info.TargetUrl)
            self.website.url_nodes[link_info.TargetUrl] = TUrlInfo(title=link_info.TargetTitle, step_name=self.robot_step.step_name)
        self.website.url_nodes[link_info.TargetUrl].parent_nodes.add(link_info.SourceUrl)
        self.website.logger.debug("add link {0}".format(link_info.TargetUrl))

    def add_downloaded_file_wrapper(self, link_info):
        self.website.url_nodes[link_info.SourceUrl].add_downloaded_file(link_info.to_json())

    def get_check_func_name(self):
        return self.step_passport['check_link_func'].__name__


class TRobotWebSite:
    panic_mode_url_count = 600
    max_step_url_count = 800

    def __init__(self, project, init_json=None):
        self.parent_project = project
        self.url_nodes = dict()
        self.logger = project.logger
        self.runtime_processed_files = dict()
        if init_json is not None:
            self.morda_url = init_json['morda_url']
            self.office_name = init_json.get('name', '')
            self.robot_steps = list()
            self.exported_files = init_json.get('exported_files', [])
            for step_no, step in enumerate(init_json.get('steps', list())):
                self.robot_steps.append(TRobotStep(project.step_names[step_no], step))
            for url, info in init_json.get('url_nodes', dict()).items():
                self.url_nodes[url] = TUrlInfo(init_json=info)
            if len(self.url_nodes) == 0:
                self.url_nodes[self.morda_url] = TUrlInfo(title=request_url_title(self.morda_url))
        else:
            self.morda_url = ""
            self.office_name = ""
            self.robot_steps = list()
            self.exported_files = []

        for step_no in range(len(self.robot_steps), len(project.step_names)):
            self.robot_steps.append(TRobotStep(project.step_names[step_no]))
        assert len(self.robot_steps) == len(project.step_names)

    def get_domain_name(self):
        return get_site_domain_wo_www(self.morda_url)

    def to_json(self):
        return {
            'morda_url': self.morda_url,
            'name': self.office_name,
            'steps': [s.to_json() for s in self.robot_steps],
            'url_nodes': dict( (url, info.to_json()) for url,info in self.url_nodes.items()),
            'exported_files': self.exported_files
        }

    def get_last_step_sha256(self):
        result = set()
        for url in self.robot_steps[-1].step_urls.keys():
            infile = get_local_file_name_by_url(url)
            if os.path.exists(infile):
                with open(infile, "rb") as f:
                    result.add(hashlib.sha256(f.read()).hexdigest())
        return result

    def get_parents(self, record):
        url = record['url']
        parents = self.url_nodes[url].parent_nodes
        if len(parents) == 0:
            raise Exception("cannot find parent for {}".format(url))
        for p in parents:
            yield p

    def get_path_to_root_recursive(self, path, all_paths):
        assert len(path) >= 1
        assert type(all_paths) is list
        tail_node = path[-1]
        url = tail_node.get('url', '')
        if url == self.morda_url:
            new_path = list(path)
            new_path.reverse()
            all_paths.append(new_path)
            return
        start = datetime.datetime.now()
        for parent_url in self.get_parents(tail_node):
            parent_url_info = self.url_nodes[parent_url]
            if url != '':
                link_info = parent_url_info.linked_nodes[url]
            else:
                link_info = tail_node['text']

            record = {
                'url': parent_url,
                'step': parent_url_info.step_name,
                'title': parent_url_info.title,
                'anchor_text': link_info['text'],
                'engine': link_info.get('engine', '')
            }
            found_in_path = False
            for u in path:
                if u['url'] == parent_url:
                    found_in_path = True
            if not found_in_path:
                self.get_path_to_root_recursive(list(path) + [record], all_paths)
            if (datetime.datetime.now() - start).total_seconds() > 2:
                break

    def get_shortest_path_to_root(self, url):
        def get_joined_path(path):
            return " ".join(u['url'] for u in path)
        url_info = self.url_nodes[url]
        path = [{'url': url, 'step': url_info.step_name}]
        all_paths = list()
        self.get_path_to_root_recursive(path, all_paths)
        if len(all_paths) == 0:
            return [{"exception": "graph is too large, timeout is set to 2 seconds"}]
        all_paths = sorted(all_paths, key=get_joined_path)
        path_lens = list(len(p) for p in all_paths)
        min_path = all_paths[path_lens.index(min(path_lens))]
        return min_path

    def get_export_folder(self):
        return os.path.join(self.parent_project.export_folder, self.get_domain_name()).replace(':', '_')

    def create_export_folder(self):
        office_folder = self.get_export_folder()
        if os.path.exists(office_folder):
            shutil.rmtree(office_folder)

    def download_last_step(self):
        for url in self.robot_steps[-1].step_urls.keys():
            try:
                read_from_cache_or_download(url)
            except Exception as err:
                self.logger.error("cannot download " + url + ": " + str(err) + "\n")
                pass

    def get_file_data_and_extension(self, url, convert_to_utf8=False):
        try:
            html = read_from_cache_or_download(url)
            extension = get_file_extension_by_cached_url(url)
            if convert_to_utf8:
                if extension == DEFAULT_HTML_EXTENSION:
                    html = convert_html_to_utf8(url, html)
            return html, extension
        except Exception as err:
            self.logger.error('cannot download page url={} while add_links, exception={}'.format(url, err))
            return None, None

    def find_a_web_page_with_a_similar_html(self, step_info, url, soup):
        html_text = str(soup)
        if len(html_text) > 1000:
            html_text = re.sub('[0-9]+', 'd', html_text)
            hash_code = "{}_{}".format(step_info.step_passport['step_name'],
                                       hashlib.sha256(html_text.encode("utf8")).hexdigest())
            already = self.runtime_processed_files.get(hash_code)
            if already is not None:
                return already
            self.runtime_processed_files[hash_code] = url
        return None

    def add_links(self, step_info, url, fallback_to_selenium=True):
        file_data, extension = self.get_file_data_and_extension(url)
        if extension != DEFAULT_HTML_EXTENSION:
            return
        try:
            soup = BeautifulSoup(file_data, "html.parser")
        except Exception as e:
            self.logger.error('cannot parse html, exception {}'.format(url, e))
            return
        already_processed = self.find_a_web_page_with_a_similar_html(step_info, url, soup)
        try:
            if already_processed is None:
                find_links_in_html_by_text(step_info, url, soup)
            else:
                self.logger.error(
                    'skip processing {} in find_links_in_html_by_text, a similar file is already processed on this step: {}'.format(url, already_processed))
                if not fallback_to_selenium and len(list(soup.findAll('a'))) < 10:
                    self.logger.debug('temporal switch on selenium, since this file can be fully javascripted')
                    fallback_to_selenium = True

            if fallback_to_selenium:  # switch off selenium is almost a panic mode (too many links)
                click_all_selenium(step_info, url, self.parent_project.selenium_driver)
        except (urllib.error.HTTPError, urllib.error.URLError, WebDriverException) as e:
            self.logger.error('add_links failed on url={}, exception: {}'.format(url, e))

    def set_fixed_list_url(self, step_info: TProcessUrlTemporary) -> bool:
        global FIXLIST
        fixed_url = FIXLIST.get(self.get_domain_name(), {}).get(step_info.step_passport['step_name'])
        if fixed_url is not None:
            link_info = TLinkInfo(TClickEngine.manual, self.morda_url, fixed_url)
            step_info.add_link_wrapper(link_info)
            return True
        return False

    @staticmethod
    def get_url_with_max_weight(d):
        max_v = TLinkInfo.MINIMAL_LINK_WEIGHT - 1.0
        best_k = None
        for k, v in d.items():
            if v >= max_v or best_k is None:
                max_v = v
                best_k = k
        return best_k

    def find_links_for_one_website_transitive(self, step_info, start_pages):
        fallback_to_selenium = step_info.step_passport.get('fallback_to_selenium', True)
        transitive = step_info.step_passport.get('transitive', False)
        processed_pages = set()
        pages_to_process = defaultdict(float)
        pages_to_process.update(start_pages)
        url_weights = list()
        for url_index in range(TRobotWebSite.max_step_url_count):
            if len(pages_to_process) == 0:
                break
            url = self.get_url_with_max_weight(pages_to_process)
            url_weight = pages_to_process[url]
            url_weights.append(url_weight)
            #the main robot stop rule
            if url_index > 300 and max(url_weights[-10:]) < 10:
                break

            self.logger.debug("max weight={}, index={}, url={} function={}".format(
                url_weight,
                url_index,
                url,
                step_info.get_check_func_name()))
            processed_pages.add(url)
            del pages_to_process[url]

            self.add_links(step_info, url, fallback_to_selenium)
            found_links_count = len(step_info.robot_step.step_urls.keys())
            if fallback_to_selenium and found_links_count >= TRobotWebSite.panic_mode_url_count:
                fallback_to_selenium = False
                self.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                    TRobotWebSite.panic_mode_url_count))
            if transitive:
                for u, w in step_info.robot_step.step_urls.items():
                    if u not in processed_pages:
                        if get_file_extension_by_cached_url(u) == DEFAULT_HTML_EXTENSION:
                            pages_to_process[u] = max(pages_to_process[u], w)

    def find_links_for_one_website(self, step_passport):
        self.logger.info(self.get_domain_name())
        step_name = step_passport['step_name']
        include_source = step_passport['include_sources']
        step_names = self.parent_project.step_names
        step_index = step_names.index(step_name)
        assert step_index != -1
        is_last_step = step_index == len(step_names) - 1
        target = self.robot_steps[step_index]
        target.step_urls = defaultdict(float)
        step_info = TProcessUrlTemporary(self, target, step_passport)
        start_time = time.time()
        if is_last_step:
            self.create_export_folder()
        if self.set_fixed_list_url(step_info):
            return

        if step_index == 0:
            start_pages = {self.morda_url: 0}
        else:
            start_pages = self.robot_steps[step_index - 1].step_urls

        if include_source == "always":
            target.step_urls.update(start_pages)

        if self.parent_project.need_search_engine_before(step_info):
            self.parent_project.use_search_engine(step_info)
            start_pages.update(target.step_urls)

        self.find_links_for_one_website_transitive(step_info, start_pages)

        if self.parent_project.need_search_engine_after(step_info):
            self.parent_project.use_search_engine(step_info)

        if include_source == "copy_if_empty" and len(target.step_urls) == 0:
            do_not_copy_urls_from_steps = step_passport.get('do_not_copy_urls_from_steps', list())
            for url, weight in start_pages.items():
                step_name = self.url_nodes[url].step_name
                if step_name not in do_not_copy_urls_from_steps:
                    target.step_urls[url] = weight

        target.profiler = {
            "elapsed_time":  time.time() - start_time,
            "step_request_rate": get_request_rate(start_time),
            "site_request_rate": get_request_rate()
        }
        self.logger.debug("{}".format(str(target.profiler)))
        target.delete_url_mirrors_by_www_and_protocol_prefix()
        self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(target.step_urls)))
