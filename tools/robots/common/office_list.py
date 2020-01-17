import hashlib
import logging
import json
import datetime
from bs4 import BeautifulSoup
from download import download_with_cache, get_site_domain_wo_www, get_local_file_name_by_url, DEFAULT_HTML_EXTENSION, \
                get_file_extension_by_cached_url

from popular_sites import is_super_popular_domain

from find_link import find_links_for_one_website, strip_viewer_prefix

FIXLIST =  {
    'fsin.su': {
        "anticorruption_div" : "http://www.fsin.su/anticorrup2014/"
    },
    'fso.gov.ru': {
        "anticorruption_div" : "http://www.fso.gov.ru/korrup.html"
    }
}



class TRobotStep:
    def __init__(self, init_json=None):
        self.logger = logging.getLogger("dlrobot_logger")
        self.found_links = dict()
        self.downloaded_files = dict()
        if init_json is not None:
            self.from_json(init_json)

    def from_json(self, r):
        self.found_links = r['links']
        self.downloaded_files = r.get('downloaded_files', [])

    def to_json(self):
        record = {
            'links': self.found_links
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = self.downloaded_files
        return record

    def add_downloaded_file(self, record):
        self.downloaded_files.append(record)

    def add_link(self, href, record):
        if record['source'] != href:
            href = strip_viewer_prefix(href)
            href = href.strip(" \r\n\t")
            domain = get_site_domain_wo_www(href)
            if not is_super_popular_domain(domain) and href.find(' ') == -1 and href.find('\n') == -1:
                if 'title' not in record:
                    try:
                        html = download_with_cache(href)
                        if get_file_extension_by_cached_url(href) == DEFAULT_HTML_EXTENSION:
                            soup = BeautifulSoup(html, "html.parser")
                            record['title'] = soup.title.string.strip(" \n\r\t")
                    except Exception as err:
                        pass
                self.found_links[href] = record
                self.logger.debug("add link {0}".format(href))

class TRobotWebSite:
    def __init__(self, init_json=None):
        self.morda_url = ""
        self.office_name = ""
        self.robot_steps = list()
        self.logger = logging.getLogger("dlrobot_logger")
        self.exported_files = []
        if init_json is not None:
            self.from_json(init_json)

    def to_json(self):
        return {
            'morda_url': self.morda_url,
            'name': self.office_name,
            'steps': [s.to_json() for s in self.robot_steps],
            'exported_files': self.exported_files
        }

    def from_json(self, r):
        self.morda_url = r['morda_url']
        self.office_name = r.get('name', '')
        self.robot_steps = []
        self.exported_files = r.get('exported_files', [])
        for x in r.get('steps', list()):
            self.robot_steps.append(TRobotStep(x))

    def get_last_step_sha256(self):
        result = set()
        for url in self.robot_steps[-1].found_links:
            infile = get_local_file_name_by_url(url)
            if os.path.exists(infile):
                with open(infile, "rb") as f:
                    result.add(hashlib.sha256(f.read()).hexdigest())
        return result


class TRobotProject:
    def __init__(self, filename, robot_steps):
        self.project_file = filename
        self.offices = list()
        self.human_files = list()
        self.names = [r['name'] for r in robot_steps]
        self.logger = logging.getLogger("dlrobot_logger")

    def write_project(self):
        with open(self.project_file, "w", encoding="utf8") as outf:
            output =  {
                'sites': [o.to_json() for o in self.offices],
                'step_names': self.names
            }
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    def read_project(self):
        self.offices = list()
        with open(self.project_file, "r", encoding="utf8") as inpf:
            json_dict = json.loads(inpf.read())
            if 'step_names'  in json_dict:
                if json_dict['step_names'] != self.names:
                    raise Exception("different step names, adjust manually or rebuild the project")

            for o in json_dict.get('sites', []):
                site = TRobotWebSite(init_json=o)
                for i in range(len(site.robot_steps), len(self.names)):
                    site.robot_steps.append(TRobotStep())
                assert len(site.robot_steps) == len(self.names)
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
            office_info.robot_steps[step_index].found_links = dict()

    @staticmethod
    def get_path_to_root(office_info, url):
        last_step = len(office_info.robot_steps) - 1
        path = []
        for i in range(last_step, 0, step=-1):
            parent = office_info.robot_steps[i].found_links.get(url)
            assert parent is not None
            url = parent['source']
            if len(path) == 0:
                path.append(parent)
            else:
                if path[-1]['source'] == url:
                    path[-1] =  parent
                else:
                    path.append(parent)
        return path

    def write_click_features(self, filename):
        result = []
        for o in self.offices:
            for url in o.robot_steps[-1].found_links:
                path = self.get_path_to_root(o, url)
                result.append(path)
        with open(filename, "w", encoding="utf8") as outf:
            json.dump(result, outf, ensure_ascii=False, indent=4)


    def download_last_step(self):
        for office_info in self.offices:
            pages_to_download = office_info.robot_steps[-1].found_links
            for url in pages_to_download:
                try:
                    if 'downloaded_file' not in pages_to_download[url]:
                        download_with_cache(url)
                except Exception as err:
                    self.logger.error("cannot download " + url + ": " + str(err) + "\n")
                    pass


    def find_links_for_all_websites(self, step_index, check_link_func, fallback_to_selenium=True,
                                    transitive=False, only_missing=True, include_source="copy_if_empty"):
        global FIXLIST
        for office_info in self.offices:
            target = office_info.robot_steps[step_index]
            step_name = self.names[step_index]
            fixed_url = FIXLIST.get(get_site_domain_wo_www(office_info.morda_url), {}).get(step_name)
            if fixed_url is not None:
                record = {'engine':'manual', 'source': 'manual', 'text':''}
                self.add_link(fixed_url, record, target)
                continue

            if len(target.found_links) > 0 and only_missing:
                self.logger.info("skip manual url updating {0}, target={1}, (already exist)\n".format(
                    office_info.office_name, target_page_collection_name))
                continue

            if step_index == 0:
                start_pages = {office_info.morda_url:{'text':""}}
            else:
                start_pages = office_info.robot_steps[step_index - 1].found_links

            if include_source == "always":
                target.found_links.update(start_pages)
            self.logger.info('{0}'.format(office_info.morda_url))
            start = datetime.datetime.now()
            find_links_for_one_website(start_pages, target,
                                       check_link_func, fallback_to_selenium, transitive)
            self.logger.info("step elapsed time {} {} {}".format (
                office_info.morda_url,
                step_name,
                (datetime.datetime.now() - start).total_seconds()))
            if include_source == "copy_if_empty" and len(target.found_links) == 0:
                target.found_links.update(start_pages)

            if include_source == "copy_docs":
                for x in start_pages:
                    if x not in target.found_links and get_file_extension_by_cached_url(x) != DEFAULT_HTML_EXTENSION:
                        target.found_links[x] = start_pages[x]

            self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(target.found_links)))


    def collect_subpages(self, step_index, check_link_func, include_source="always"):
        self.find_links_for_all_websites(step_index,
                                    check_link_func,
                                    fallback_to_selenium=False,
                                    transitive=True,
                                    only_missing=False,
                                    include_source=include_source)
