import hashlib
import logging
import json
import shutil
import os
import tempfile
import urllib
import time
import operator
from bs4 import BeautifulSoup
from robots.common.download import read_from_cache_or_download, get_site_domain_wo_www, get_local_file_name_by_url, DEFAULT_HTML_EXTENSION, \
                get_file_extension_by_cached_url, ACCEPTED_DECLARATION_FILE_EXTENSIONS, convert_html_to_utf8

from robots.common.http_request import get_request_rate
from robots.common.export_files import DL_RECOGNIZER_UNKNOWN
from robots.common.selenium_driver import TSeleniumDriver
from robots.common.find_link import strip_viewer_prefix, click_all_selenium, can_be_office_document, \
                    find_links_in_html_by_text, common_link_check


from robots.common.serp_parser import GoogleSearch
from collections import defaultdict

FIXLIST =  {
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


class TRobotStep:
    def __init__(self, step_name, init_json=None):
        self.step_name = step_name
        self.profiler = dict()
        if init_json  is not None:
            self.step_urls = set(init_json.get('step_urls', list()))
            self.profiler = init_json.get('profiler', dict())
        else:
            self.step_urls = set()

    def delete_url_mirrors(self):
        mirrors = defaultdict(list)
        for u in self.step_urls:
            m = TUrlMirror(u)
            mirrors[m.normalized_url].append(m)
        self.step_urls = set()
        for urls in mirrors.values():
            urls = sorted(urls, key=(lambda x: len(x.input_url)))
            self.step_urls.add(urls[-1].input_url)  # get the longest url

    def to_json(self):
        return {
            'step_name': self.step_name,
            'step_urls': list(self.step_urls),
            'profiler': self.profiler
        }


class TUrlInfo:
    def __init__(self, title=None, step_name=None, init_json=None):
        if init_json is not None:
            self.step_name = init_json['step']
            self.title = init_json['title']
            self.parent_nodes = set(init_json.get('parents', list()))
            self.linked_nodes = init_json.get('links', dict())
            self.downloaded_files = init_json.get('downloaded_files', list())
            self.dl_recognizer_result = init_json.get('dl_recognizer_result', DL_RECOGNIZER_UNKNOWN)
        else:
            self.step_name = step_name
            self.title = title
            self.parent_nodes = set()
            self.linked_nodes = dict()
            self.downloaded_files = list()
            self.dl_recognizer_result = DL_RECOGNIZER_UNKNOWN

    def to_json(self):
        record = {
            'step': self.step_name,
            'title': self.title,
            'parents': list(self.parent_nodes),
            'links': self.linked_nodes,
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = self.downloaded_files
        if self.dl_recognizer_result != DL_RECOGNIZER_UNKNOWN:
            record['dl_recognizer_result'] = self.dl_recognizer_result
        return record

    def add_downloaded_file(self, record):
        self.downloaded_files.append(record)

    def add_link(self, href, record):
        self.linked_nodes[href] = record


def request_url_title(url):
    try:
        html = read_from_cache_or_download(url)
        if get_file_extension_by_cached_url(url) == DEFAULT_HTML_EXTENSION:
            soup = BeautifulSoup(html, "html.parser")
            return soup.title.string.strip(" \n\r\t")
    except Exception as err:
        return ""


class TRobotWebSite:
    def __init__(self, step_names, init_json=None):
        self.url_nodes = dict()
        self.logger = logging.getLogger("dlrobot_logger")
        if init_json is not None:
            self.morda_url = init_json['morda_url']
            self.office_name = init_json.get('name', '')
            self.robot_steps = list()
            self.exported_files = init_json.get('exported_files', [])
            for step_no, step in enumerate(init_json.get('steps', list())):
                self.robot_steps.append(TRobotStep(step_names[step_no], step))
            for url, info in init_json.get('url_nodes', dict()).items():
                self.url_nodes[url] = TUrlInfo(init_json=info)
            if len(self.url_nodes) == 0:
                self.url_nodes[self.morda_url] = TUrlInfo(title=request_url_title(self.morda_url))
        else:
            self.morda_url = ""
            self.office_name = ""
            self.robot_steps = list()
            self.exported_files = []

        for step_no in range(len(self.robot_steps), len(step_names)):
            self.robot_steps.append(TRobotStep(step_names[step_no]))
        assert len(self.robot_steps) == len(step_names)

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
        for url in self.robot_steps[-1].step_urls:
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


    def get_shortest_path_to_root(self, url):
        url_info = self.url_nodes[url]
        path = [{'url': url, 'step': url_info.step_name}]
        all_paths = list()
        self.get_path_to_root_recursive(path, all_paths)
        assert len(all_paths) > 0
        path_lens = list(len(p) for p in all_paths)
        min_path = all_paths[path_lens.index(min(path_lens))]
        return min_path


class TProcessUrlTemporary:
    def __init__(self, website, robot_step, step_passport):
        self.website = website
        self.check_link_func = step_passport['check_link_func']
        self.robot_step = robot_step
        self.step_passport = step_passport

    def add_link_wrapper(self, source, link_info):
        href = link_info.pop('href')
        if not common_link_check(href):
            self.website.logger.debug('skip {} since it looks like a print link or it is an external url'.format(href))
            return

        href = strip_viewer_prefix(href)
        href = href.strip(" \r\n\t")
        if source == href:
            return

        href_title = link_info.pop('title') if 'title' in link_info else request_url_title(href)

        self.website.url_nodes[source].add_link(href, link_info)
        self.robot_step.step_urls.add(href)

        if href not in self.website.url_nodes:
            self.website.url_nodes[href] = TUrlInfo(title=href_title, step_name=self.robot_step.step_name)
        new_node = self.website.url_nodes[href]
        new_node.parent_nodes.add(source)
        self.website.logger.debug("add link {0}".format(href))

    def add_downloaded_file_wrapper(self, source, record):
        self.website.url_nodes[source].add_downloaded_file(record)



class TRobotProject:
    logger = None
    selenium_driver = TSeleniumDriver()
    step_names = list()
    panic_mode_url_count = 400
    max_step_url_count = 800

    def __init__(self, filename, robot_steps):
        self.project_file = filename + ".clicks"
        if not os.path.exists(self.project_file):
            shutil.copy2(filename, self.project_file)
        self.offices = list()
        self.human_files = list()
        TRobotProject.step_names = [r['step_name'] for r in robot_steps]
        self.enable_search_engine = True  #switched off in tests, otherwize google shows captcha

    def __enter__(self):
        TRobotProject.logger = logging.getLogger("dlrobot_logger")
        TRobotProject.selenium_driver.download_folder = tempfile.mkdtemp()
        TRobotProject.selenium_driver.start_executable()
        return self

    def __exit__(self, type, value, traceback):
        TRobotProject.selenium_driver.stop_executable()
        shutil.rmtree(TRobotProject.selenium_driver.download_folder)


    def write_project(self):
        with open(self.project_file, "w", encoding="utf8") as outf:
            output =  {
                'sites': [o.to_json() for o in self.offices],
                'step_names': self.step_names
            }
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    def read_project(self):
        self.offices = list()
        with open(self.project_file, "r", encoding="utf8") as inpf:
            json_dict = json.loads(inpf.read())
            if 'step_names'  in json_dict:
                if json_dict['step_names'] != self.step_names:
                    raise Exception("different step step_names, adjust manually or rebuild the project")

            for o in json_dict.get('sites', []):
                site = TRobotWebSite(self.step_names, init_json=o)
                self.offices.append(site)
            if "disable_search_engine" in json_dict:
                self.enable_search_engine = False

    def read_human_files(self, filename):
        self.human_files = list()
        with open(filename, "r", encoding="utf8") as inpf:
            self.human_files = json.load(inpf)

    def check_all_offices(self):
        for o in self.offices:
            main_domain = o.get_domain_name()
            self.logger.debug("check_recall for {}".format(main_domain))
            robot_sha256 = o.get_last_step_sha256()
            files_count = 0
            found_files_count = 0
            for x in self.human_files:
                if len(x['domain']) > 0:
                    domain = get_site_domain_wo_www(x['domain'])
                    if domain == main_domain or main_domain.endswith(domain) or domain.endswith(main_domain):
                        for s in x['sha256']:
                            files_count += 1
                            if s not in robot_sha256:
                                self.logger.debug("{0} not found from {1}".format(s, json.dumps(x)))
                            else:
                                found_files_count += 1
            self.logger.info(
                "all human files = {}, human files found by dlrobot = {}".format(files_count, found_files_count))

    def write_click_features(self, filename):
        self.logger.info("create {}".format(filename))
        result = []
        for office_info in self.offices:
            downloaded_files_count =  sum(len(v.downloaded_files) for v in office_info.url_nodes.values())
            self.logger.info("find useless nodes in {}".format(office_info.morda_url))
            self.logger.info("all url nodes and downloaded with selenium: {}".format(
                len(office_info.url_nodes) + downloaded_files_count))
            for url, info in office_info.url_nodes.items():
                if len(info.downloaded_files) > 0:
                    for d in info.downloaded_files:
                        path = office_info.get_shortest_path_to_root(url)
                        file_info = dict(d.items())
                        file_info['url'] = 'element_index:{}. url:{}'.format(d['element_index'], url)
                        path.append(file_info)
                        result.append({
                            'dl_recognizer_result': d['dl_recognizer_result'],
                            'path': path
                        })
                elif len(info.linked_nodes) == 0:
                    path = office_info.get_path_to_root(url)
                    result.append({
                        'dl_recognizer_result': info.dl_recognizer_result,
                        'path': path
                    })
            useful_nodes = {p['url'] for r in result if r['dl_recognizer_result'] > 0 for p in r['path'] }
            self.logger.info("useful nodes: {}".format(len(useful_nodes)))

        with open(filename, "w", encoding="utf8") as outf:
            json.dump(result, outf, ensure_ascii=False, indent=4)

    def download_last_step(self):
        for office_info in self.offices:
            for url in office_info.robot_steps[-1].step_urls:
                try:
                    read_from_cache_or_download(url)
                except Exception as err:
                    self.logger.error("cannot download " + url + ": " + str(err) + "\n")
                    pass

    def write_export_stats(self):
        result = list()
        for office_info in self.offices:
            for export_record in office_info.exported_files:
                path = office_info.get_shortest_path_to_root(export_record['url'])
                rec = {
                    'click_path': path,
                    'cached_file': export_record['cached_file'].replace('\\', '/'),
                    'sha256': export_record['sha256'],
                    'dl_recognizer_result': export_record['dl_recognizer_result'],
                }
                result.append(rec)
        result = sorted(result, key=(lambda x: x['sha256']))
        with open(self.project_file + ".stats", "w", encoding="utf8") as outf:
            summary = {
                "files_count": len(result)
            }
            result.insert(0, summary)
            json.dump(result, outf, ensure_ascii=False, indent=4)

    @staticmethod
    def find_links_with_selenium (step_info, main_url):
        if can_be_office_document(main_url):
            return
        click_all_selenium(step_info, main_url, TRobotProject.selenium_driver)

    @staticmethod
    def get_file_data_and_extension(url, convert_to_utf8=False):
        try:
            html = read_from_cache_or_download(url)
            extension = get_file_extension_by_cached_url(url)
            if convert_to_utf8:
                if extension == DEFAULT_HTML_EXTENSION:
                    html = convert_html_to_utf8(url, html)
            return html, extension
        except Exception as err:
            TRobotProject.logger.error('cannot download page url={} while add_links, exception={}'.format(url, str(err)))
            return None, None

    @staticmethod
    def add_links(step_info, url, fallback_to_selenium=True):
        file_data, extension = TRobotProject.get_file_data_and_extension(url)
        if extension != DEFAULT_HTML_EXTENSION:
            return

        try:
            soup = BeautifulSoup(file_data, "html.parser")

            save_links_count = len(step_info.robot_step.step_urls)
            find_links_in_html_by_text(step_info, url, soup)

            # see http://minpromtorg.gov.ru/docs/#!svedeniya_o_dohodah_rashodah_ob_imushhestve_i_obyazatelstvah_imushhestvennogo_haraktera_federalnyh_gosudarstvennyh_grazhdanskih_sluzhashhih_minpromtorga_rossii_rukovodstvo_a_takzhe_ih_suprugi_supruga_i_nesovershennoletnih_detey_za_period_s_1_yanvarya_2018_g_po_31_dekabrya_2018_g
            if save_links_count == len(step_info.robot_step.step_urls) and fallback_to_selenium:
                TRobotProject.find_links_with_selenium(step_info, url)

        except (TypeError, NameError, IndexError,  KeyError, AttributeError) as err:
            raise err
        except Exception as err:
            TRobotProject.logger.error('cannot download page url={0} while find_links, exception={1}'.format(url, str(err)))

    @staticmethod
    def find_links_for_one_website_transitive(step_info, start_pages):
        fallback_to_selenium = step_info.step_passport.get('fallback_to_selenium', True)
        transitive = step_info.step_passport.get('transitive', False)
        while True:
            save_count = len(step_info.robot_step.step_urls)

            for url in start_pages:
                TRobotProject.add_links(step_info, url, fallback_to_selenium)

                found_links_count = len(step_info.robot_step.step_urls)
                if fallback_to_selenium and found_links_count >= TRobotProject.panic_mode_url_count:
                    fallback_to_selenium = False
                    TRobotProject.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                        TRobotProject.panic_mode_url_count))
                if found_links_count >= TRobotProject.max_step_url_count:
                    TRobotProject.logger.error("too many links (>{}),  stop processing step {}".format(
                        TRobotProject.max_step_url_count,
                        step_info.robot_step.step_name))
                    return
            new_count = len(step_info.robot_step.step_urls)
            if not transitive or save_count == new_count:
                return

    @staticmethod
    def try_use_search_engine(step_info):
        request = step_info.step_passport.get('search_engine_request')
        if request is None:
            return
        min_normal_count = step_info.step_passport.get('min_normal_count', 1)
        if len(step_info.robot_step.step_urls) >= min_normal_count:
            return
        TRobotProject.logger.info('search engine request: {}'.format(request))
        morda_url = step_info.website.morda_url
        site = step_info.website.get_domain_name()
        links_count = 0
        try:
            serp_urls = GoogleSearch.site_search(site, request, TRobotProject.selenium_driver)
        except urllib.error.HTTPError as err:
            TRobotProject.logger.error('cannot request search engine, exception {}'.format(str(err)))
            return

        for url in serp_urls:
            link_info = {
                'engine': 'google',
                'text': request,
                'href': url
            }
            step_info.add_link_wrapper(morda_url, link_info)
            if min_normal_count == 1:
                break  # one  link found
            links_count += 1
        TRobotProject.logger.info('found {} links using search engine'.format(links_count))

    @staticmethod
    def check_html_sources(step_info, start_pages):
        check_func = step_info.step_passport.get('check_html_sources')
        assert check_func is not None
        for url in start_pages:
            file_data, extenstion = TRobotProject.get_file_data_and_extension(url, convert_to_utf8=True)
            if extenstion == DEFAULT_HTML_EXTENSION and check_func(file_data):
                TRobotProject.logger.debug("add url {} by {}".format(url, check_func.__name__))
                step_info.robot_step.step_urls.add(url)



    def find_links_for_one_website(self, office_info, step_passport):
        global FIXLIST
        step_name = step_passport['step_name']
        include_source = step_passport['include_sources']
        step_index = self.step_names.index(step_name)
        assert step_index != -1
        office_info.robot_steps[step_index].step_urls = set()
        target = office_info.robot_steps[step_index]
        target.step_urls = set()
        step_info = TProcessUrlTemporary(office_info, target, step_passport)
        start_time = time.time()

        fixed_url = FIXLIST.get(office_info.get_domain_name(), {}).get(step_name)
        if fixed_url is not None:
            link_info = {
                'engine': 'manual',
                'text': '',
                'href': fixed_url
            }
            step_info.add_link_wrapper(office_info.morda_url, link_info)
            return

        if step_index == 0:
            start_pages = {office_info.morda_url}
        else:
            start_pages = office_info.robot_steps[step_index - 1].step_urls

        if include_source == "always":
            target.step_urls.update(start_pages)

        self.find_links_for_one_website_transitive(step_info, start_pages)
        if self.enable_search_engine:
            self.try_use_search_engine(step_info)

        if include_source == "copy_if_empty" and len(target.step_urls) == 0:
            do_not_copy_urls_from_steps = step_passport.get('do_not_copy_urls_from_steps', list())
            for url in start_pages:
                step_name = office_info.url_nodes[url].step_name
                if step_name not in do_not_copy_urls_from_steps:
                    target.step_urls.add(url)

        if include_source == "copy_missing_docs":
            for url in start_pages:
                if url not in target.step_urls:
                    ext = get_file_extension_by_cached_url(url)
                    if ext != DEFAULT_HTML_EXTENSION and ext in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
                        target.step_urls.add(url)

        if step_passport.get('check_html_sources') is not None:
            TRobotProject.check_html_sources(step_info, start_pages)
        target.profiler = {
            "elapsed_time":  time.time() - start_time,
            "step_request_rate": get_request_rate(start_time),
            "site_request_rate": get_request_rate()
        }
        target.delete_url_mirrors()
        self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(target.step_urls)))
