import json
import shutil
import os
import tempfile
import urllib.error
from robots.common.selenium_driver import TSeleniumDriver
from robots.common.find_link import TLinkInfo, TClickEngine
from robots.common.serp_parser import GoogleSearch
from robots.common.web_site import TRobotWebSite, TRobotStep


class TRobotProject:
    selenium_driver = TSeleniumDriver()

    def __init__(self, logger, filename, robot_step_passports, export_folder):
        self.logger = logger
        self.project_file = filename + ".clicks"
        if not os.path.exists(self.project_file):
            shutil.copy2(filename, self.project_file)
        self.offices = list()
        self.human_files = list()
        self.robot_step_passports = robot_step_passports
        self.enable_search_engine = True  #switched off in tests, otherwize google shows captcha
        self.export_folder = export_folder

    def get_robot_step_names(self):
        return list(r['step_name'] for r in self.robot_step_passports)

    def __enter__(self):
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
                'step_names': self.get_robot_step_names()
            }
            if not self.enable_search_engine:
                output["disable_search_engine"] = True
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    def read_project(self):
        self.offices = list()
        with open(self.project_file, "r", encoding="utf8") as inpf:
            json_dict = json.loads(inpf.read())
            if 'step_names' in json_dict:
                if json_dict['step_names'] != self.get_robot_step_names():
                    raise Exception("different step step_names, adjust manually or rebuild the project")

            for o in json_dict.get('sites', []):
                site = TRobotWebSite(self, init_json=o)
                self.offices.append(site)
            if "disable_search_engine" in json_dict:
                self.enable_search_engine = False

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
                if 'name_in_archive' in export_record:
                    rec['name_in_archive'] = export_record['name_in_archive']
                result.append(rec)
        result = sorted(result, key=(lambda x: x['sha256']))
        with open(self.project_file + ".stats", "w", encoding="utf8") as outf:
            summary = {
                "files_count": len(result)
            }
            result.insert(0, summary)
            json.dump(result, outf, ensure_ascii=False, indent=4)

    def use_search_engine(self, step_info):
        request = step_info.step_passport['search_engine']['request']
        max_results = step_info.step_passport['search_engine'].get('max_serp_results', 10)
        self.logger.info('search engine request: {}'.format(request))
        morda_url = step_info.website.morda_url
        site = step_info.website.get_domain_name()
        links_count = 0
        try:
            serp_urls = GoogleSearch.site_search(site, request, TRobotProject.selenium_driver)
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            self.logger.error('cannot request search engine, exception {}'.format(err))
            return

        for url in serp_urls:
            link_info = TLinkInfo(TClickEngine.google, morda_url, url, anchor_text=request)
            link_info.Weight = TLinkInfo.MINIMAL_LINK_WEIGHT + 1  # > 0
            step_info.add_link_wrapper(link_info)
            if max_results == 1:
                break  # one  link found
            links_count += 1
        self.logger.info('found {} links using search engine'.format(links_count))

    def need_search_engine_before(self, step_info: TRobotStep):
        if not self.enable_search_engine:
            return False
        policy = step_info.step_passport.get('search_engine', dict()).get('policy','')
        return policy == "run_always_before"

    def need_search_engine_after(self, step_info: TRobotStep):
        if not self.enable_search_engine:
            return False
        policy = step_info.step_passport.get('search_engine', dict()).get('policy','')
        return policy == "run_after_if_no_results" and len(step_info.step_urls) == 0

