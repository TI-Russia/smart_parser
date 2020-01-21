import hashlib
import logging
import json
import datetime
import shutil
import os
import tempfile
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from download import download_with_cache, get_site_domain_wo_www, get_local_file_name_by_url, DEFAULT_HTML_EXTENSION, \
                get_file_extension_by_cached_url

from popular_sites import is_super_popular_domain

from find_link import strip_viewer_prefix, click_all_selenium, can_be_office_document, \
                    find_links_in_html_by_text

from content_types import  ALL_CONTENT_TYPES

FIXLIST =  {
    'fsin.su': {
        "anticorruption_div" : "http://www.fsin.su/anticorrup2014/"
    },
    'fso.gov.ru': {
        "anticorruption_div" : "http://www.fso.gov.ru/korrup.html"
    }
}


class TRobotStep:
    def __init__(self, step_name, init_json=None):
        self.step_name = step_name
        if init_json  is not None:
            self.step_urls = set(init_json.get('step_urls', []))
        else:
            self.step_urls = set()

    def to_json(self):
        return {
            'step_urls': list(self.step_urls)
        }


class TUrlInfo:
    def __init__(self, title=None, step_name=None, init_json=None):
        if init_json is not None:
            self.step_name = init_json['step']
            self.title = init_json['title']
            self.parent_nodes = set(init_json.get('parents', list()))
            self.linked_nodes = init_json.get('links', dict())
            self.downloaded_files = init_json.get('downloaded_files', list())
            self.people_count = init_json.get('people_count', -1)
        else:
            self.step_name = step_name
            self.title = title
            self.parent_nodes = set()
            self.linked_nodes = dict()
            self.downloaded_files = list()
            self.people_count = -1

    def to_json(self):
        record = {
            'step': self.step_name,
            'title': self.title,
            'parents': list(self.parent_nodes),
            'links': self.linked_nodes,
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = self.downloaded_files
        if self.people_count != -1:
            record['people_count'] = self.people_count
        return record

    def add_downloaded_file(self, record):
        self.downloaded_files.append(record)

    def add_link(self, href, record):
        self.linked_nodes[href] = record


def request_url_title(url):
    try:
        html = download_with_cache(url)
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
                self.url_nodes[self.morda_url] = TUrlInfo(title=get_title(self.morda_url))
        else:
            self.morda_url = ""
            self.office_name = ""
            self.robot_steps = list()
            self.exported_files = []

        for step_no in range(len(self.robot_steps), len(step_names)):
            self.robot_steps.append(TRobotStep(step_names[step_no]))
        assert len(self.robot_steps) == len(step_names)


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


    def get_path_to_root_recursive(self, path):
        assert len(path) >= 1
        tail_node = path[-1]
        url = tail_node.get('url', '')
        if url == self.morda_url:
            return True
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
                'anchor_text': link_info['text']
            }

            if parent_url not in {u['url'] for u in path}:
                new_path = list(path) + [record]
                if self.get_path_to_root_recursive(new_path):
                    path.clear()
                    path.extend(new_path)
                    return True
        return False

    def get_path_to_root(self, url):
        url_info = self.url_nodes[url]
        path = [{'url': url, 'step': url_info.step_name}]
        found_root = self.get_path_to_root_recursive(path)
        assert found_root
        path.reverse()
        return path

def open_selenium(tmp_folder):
    options = FirefoxOptions()
    options.headless = True
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.manager.closeWhenDone", True)
    options.set_preference("browser.download.manager.focusWhenStarting", False)
    options.set_preference("browser.download.dir", tmp_folder)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", ALL_CONTENT_TYPES)
    options.set_preference("browser.helperApps.alwaysAsk.force", False)
    return webdriver.Firefox(firefox_options=options)


class TProcessUrlTemporary:
    def __init__(self, website, check_link_func, robot_step):
        self.website = website
        self.check_link_func = check_link_func
        self.robot_step = robot_step

    def add_link_wrapper(self, source, link_info):
        href = link_info.pop('href')
        if is_super_popular_domain(get_site_domain_wo_www(href)) or href.find(' ') != -1 or href.find('\n') != -1:
            return
        if href.find('print=') != -1:
            self.website.logger.debug('skip {} since it looks like a print link, that causes a print dialog'.format(href))
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
    selenium_driver = None
    selenium_download_folder = None
    step_names = list()

    def __init__(self, filename, robot_steps):
        self.project_file = filename + ".clicks"
        if not os.path.exists(self.project_file):
            shutil.copy2(filename, self.project_file)
        self.offices = list()
        self.human_files = list()
        TRobotProject.step_names = [r['name'] for r in robot_steps]

    def __enter__(self):
        TRobotProject.logger = logging.getLogger("dlrobot_logger")
        TRobotProject.selenium_download_folder = tempfile.mkdtemp()
        TRobotProject.selenium_driver = open_selenium(TRobotProject.selenium_download_folder)
        return self

    def __exit__(self, type, value, traceback):
        if TRobotProject.selenium_driver is not None:
            TRobotProject.selenium_driver.quit()
        shutil.rmtree(TRobotProject.selenium_download_folder)


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

    def read_human_files(self, filename):
        self.human_files = list()
        with open(filename, "r", encoding="utf8") as inpf:
            self.human_files = json.load(inpf)

    def create_by_hypots(self, filename):
        self.offices = list()
        with open (filename, "r", encoding="utf8") as inpf:
            for x in inpf:
                url = x.strip()
                if len(url) == 0:
                    continue
                domain = "http://" + get_site_domain_wo_www(x.strip())
                site = TRobotWebSite()
                site.morda_url = domain
                self.offices.append(site)
        self.write_project()

    def check_all_offices(self):

        for o in self.offices:
            main_url = o.morda_url
            main_domain = get_site_domain_wo_www(main_url)
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

    def del_old_info(self, step_index):
        for office_info in self.offices:
            office_info.robot_steps[step_index].step_urls = set()

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
                        path = office_info.get_path_to_root(url)
                        file_info = dict(d.items())
                        file_info['url'] = 'element_index:{}. url:{}'.format(d['element_index'], url)
                        path.append(file_info)
                        result.append({
                            'people_count': d['people_count'],
                            'path': path
                        })
                elif len(info.linked_nodes) == 0:
                    path = office_info.get_path_to_root(url)
                    result.append({
                        'people_count': info.people_count,
                        'path': path
                    })
            useful_nodes = {p['url'] for r in result if r['people_count'] > 0 for p in r['path'] }
            self.logger.info("useful nodes: {}".format(len(useful_nodes)))

        with open(filename, "w", encoding="utf8") as outf:
            json.dump(result, outf, ensure_ascii=False, indent=4)

    def download_last_step(self):
        for office_info in self.offices:
            for url in office_info.robot_steps[-1].step_urls:
                try:
                    download_with_cache(url)
                except Exception as err:
                    self.logger.error("cannot download " + url + ": " + str(err) + "\n")
                    pass


    def collect_subpages(self, step_index, check_link_func, include_source="always"):
        self.find_links_for_all_websites(step_index,
                                    check_link_func,
                                    fallback_to_selenium=False,
                                    transitive=True,
                                    only_missing=False,
                                    include_source=include_source)

    def write_export_stats(self):
        result = list()
        for o in self.offices:
            for export_record in o.exported_files:
                result.append( (export_record['infile'],  export_record['people_count']))
        result = sorted (result)
        with open (self.project_file + ".stats", "w", encoding="utf8") as outf:
            json.dump(result, outf, indent=4)

    @staticmethod
    def find_links_with_selenium (step_info, main_url):
        if can_be_office_document(main_url):
            return
        click_all_selenium(step_info, main_url,
                           TRobotProject.selenium_driver,
                           TRobotProject.selenium_download_folder   )


    @staticmethod
    def add_links(step_info, url, fallback_to_selenium=True):
        html = ""
        try:
            html = download_with_cache(url)
        except Exception as err:
            TRobotProject.logger.error('cannot download page url={0} while add_links, exception={1}\n'.format(url, str(err)))
            return

        if get_file_extension_by_cached_url(url) != DEFAULT_HTML_EXTENSION:
            TRobotProject.logger.debug("cannot get links  since it is not html: {0}".format(url))
            return

        try:
            soup = BeautifulSoup(html, "html.parser")

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
    def find_links_for_one_website(step_info, start_pages, fallback_to_selenium, transitive):
        while True:
            save_count = len(step_info.robot_step.step_urls)

            for url in start_pages:
                TRobotProject.add_links(step_info, url, fallback_to_selenium)

            new_count = len(step_info.robot_step.step_urls)
            if not transitive or save_count == new_count:
                break


    def find_links_for_all_websites(self, step_index, check_link_func, fallback_to_selenium=True,
                                    transitive=False, only_missing=True, include_source="copy_if_empty"):
        global FIXLIST
        for office_info in self.offices:
            target = office_info.robot_steps[step_index]
            step_name = self.step_names[step_index]
            step_info = TProcessUrlTemporary(office_info, check_link_func, target)

            fixed_url = FIXLIST.get(get_site_domain_wo_www(office_info.morda_url), {}).get(step_name)
            if fixed_url is not None:
                link_info = {
                    'engine': 'manual',
                    'text': '',
                    'href': fixed_url
                }
                step_info.add_link_wrapper(office_info.morda_url, link_info)
                continue

            if len(target.step_urls) > 0 and only_missing:
                self.logger.info("skip manual url updating {0}, target={1}, (already exist)\n".format(
                    office_info.office_name, target_page_collection_name))
                continue

            if step_index == 0:
                start_pages = {office_info.morda_url}
            else:
                start_pages = office_info.robot_steps[step_index - 1].step_urls

            if include_source == "always":
                target.step_urls.update(start_pages)
            self.logger.info('{0}'.format(office_info.morda_url))
            start = datetime.datetime.now()
            self.find_links_for_one_website(step_info,
                                       start_pages,
                                       fallback_to_selenium,
                                       transitive)
            self.logger.info("step elapsed time {} {} {}".format (
                office_info.morda_url,
                step_name,
                (datetime.datetime.now() - start).total_seconds()))
            if include_source == "copy_if_empty" and len(target.step_urls) == 0:
                target.step_urls.update(start_pages)

            self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(target.step_urls)))
