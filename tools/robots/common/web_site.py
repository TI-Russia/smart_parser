from robots.common.download import get_local_file_name_by_url, request_url_title, read_from_cache_or_download,  \
                DEFAULT_HTML_EXTENSION, get_file_extension_by_cached_url,  convert_html_to_utf8
from collections import defaultdict
from robots.common.primitives import get_site_domain_wo_www
import os
import shutil
import time
import datetime
from robots.common.http_request import get_request_rate
import hashlib
import re
from robots.common.find_link import TLinkInfo, TClickEngine
from robots.common.robot_step import TRobotStep, TUrlInfo

FIXLIST = {
    'fsin.su': {
        "anticorruption_div": "http://www.fsin.su/anticorrup2014/"
    },
    'fso.gov.ru': {
        "anticorruption_div": "http://www.fso.gov.ru/korrup.html"
    }
}


class TRobotWebSite:

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
                self.robot_steps.append(TRobotStep(self, project.robot_step_passports[step_no], init_json=step))
            for url, info in init_json.get('url_nodes', dict()).items():
                self.url_nodes[url] = TUrlInfo(init_json=info)
            if len(self.url_nodes) == 0:
                self.url_nodes[self.morda_url] = TUrlInfo(title=request_url_title(self.morda_url))
        else:
            self.morda_url = ""
            self.office_name = ""
            self.robot_steps = list()
            self.exported_files = []
        if len(self.robot_steps) == 0:
            for p in project.robot_step_passports:
                self.robot_steps.append(TRobotStep(self, p))
        assert len(self.robot_steps) == len(project.robot_step_passports)

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

    def find_a_web_page_with_a_similar_html(self, step_info: TRobotStep, url, soup):
        html_text = str(soup)
        if len(html_text) > 1000:
            html_text = re.sub('[0-9]+', 'd', html_text)
            hash_code = "{}_{}".format(step_info.get_step_name(),
                                       hashlib.sha256(html_text.encode("utf8")).hexdigest())
            already = self.runtime_processed_files.get(hash_code)
            if already is not None:
                return already
            self.runtime_processed_files[hash_code] = url
        return None

    def set_fixed_list_url(self, step_info: TRobotStep) -> bool:
        global FIXLIST
        fixed_url = FIXLIST.get(self.get_domain_name(), {}).get(step_info.get_step_name())
        if fixed_url is not None:
            link_info = TLinkInfo(TClickEngine.manual, self.morda_url, fixed_url)
            step_info.add_link_wrapper(link_info)
            return True
        return False

    def find_links_for_one_website(self, step_index: int):
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
        if self.set_fixed_list_url(target):
            return

        if step_index == 0:
            start_pages = {self.morda_url: 0}
        else:
            start_pages = self.robot_steps[step_index - 1].step_urls

        if include_source == "always":
            target.step_urls.update(start_pages)

        if self.parent_project.need_search_engine_before(target):
            self.parent_project.use_search_engine(target)
            start_pages.update(target.step_urls)

        target.find_links_for_one_website_transitive(start_pages)

        if self.parent_project.need_search_engine_after(target):
            self.parent_project.use_search_engine(target)

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
