import json
import shutil
import os
import tempfile
import time
from robots.common.selenium_driver import TSeleniumDriver
from robots.common.link_info import TLinkInfo, TClickEngine
from robots.common.serp_parser import SearchEngine, SearchEngineEnum, SerpException
from robots.common.web_site import TRobotWebSite, TRobotStep
from robots.common.http_request import RobotHttpException
from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException


class TRobotProject:

    def __init__(self, logger, filename, robot_step_passports, export_folder, enable_selenium=True, enable_search_engine=True):
        self.logger = logger
        self.selenium_driver = TSeleniumDriver(logger)
        self.project_file = filename + ".clicks"
        if not os.path.exists(self.project_file):
            shutil.copy2(filename, self.project_file)
        self.offices = list()
        self.human_files = list()
        self.robot_step_passports = robot_step_passports
        self.enable_search_engine = enable_search_engine  #switched off in tests, otherwize google shows captcha
        self.export_folder = export_folder
        self.enable_selenium = enable_selenium

    def get_robot_step_names(self):
        return list(r['step_name'] for r in self.robot_step_passports)

    def __enter__(self):
        if self.enable_selenium:
            self.selenium_driver.download_folder = tempfile.mkdtemp()
            self.selenium_driver.start_executable()
        return self

    def __exit__(self, type, value, traceback):
        if self.enable_selenium:
            self.selenium_driver.stop_executable()
            shutil.rmtree(self.selenium_driver.download_folder)

    def write_project(self):
        with open(self.project_file, "w", encoding="utf8") as outf:
            output =  {
                'sites': [o.to_json() for o in self.offices],
                'step_names': self.get_robot_step_names()
            }
            if not self.enable_search_engine:
                output["disable_search_engine"] = True
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    def add_office(self, morda_url):
        office_info = TRobotWebSite(self)
        office_info.morda_url = morda_url
        self.offices.append(office_info)

    def read_project(self, fetch_morda_url=True, check_step_names=True):
        self.offices = list()
        with open(self.project_file, "r", encoding="utf8") as inpf:
            json_dict = json.loads(inpf.read())
            if check_step_names:
                if 'step_names' in json_dict:
                    if json_dict['step_names'] != self.get_robot_step_names():
                        raise Exception("different step step_names, adjust manually or rebuild the project")
            else:
                self.robot_step_passports = list()
                for step_name in json_dict['step_names']:
                    self.robot_step_passports.append(step_name)

            for o in json_dict.get('sites', []):
                site = TRobotWebSite(self, init_json=o)
                if fetch_morda_url:
                    site.init_morda_url_if_necessary()

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
        files_with_click_path = list()
        for office_info in self.offices:
            for export_record in office_info.export_env.exported_files:
                path = office_info.get_shortest_path_to_root(export_record.url)
                rec = {
                    'click_path': path,
                    'cached_file': export_record.cached_file.replace('\\', '/'),
                    'sha256': export_record.sha256
                }
                if export_record.archive_index != -1:
                    rec['archive_index'] = export_record.archive_index
                files_with_click_path.append(rec)
        files_with_click_path.sort(key=(lambda x: x['sha256']))
        cached_files = list("{} {}".format(x['cached_file'], x.get('archive_index', -1)) for x in files_with_click_path)
        cached_files.sort()
        with open(self.project_file + ".stats", "w", encoding="utf8") as outf:
            report = {
                "files_count": len(cached_files),
                "files_sorted (short report)": cached_files,
                "files_with_click_path (full report)": files_with_click_path
            }
            json.dump(report, outf, ensure_ascii=False, indent=4)


    def use_search_engine(self, step_info):
        request = step_info.step_passport['search_engine']['request']
        max_results = step_info.step_passport['search_engine'].get('max_serp_results', 10)
        self.logger.info('search engine request: {}'.format(request))
        morda_url = step_info.website.morda_url
        site = step_info.website.get_domain_name()
        serp_urls = list()
        for search_engine in range (0, SearchEngineEnum.SearchEngineCount):
            try:
                serp_urls = SearchEngine.site_search(search_engine, site, request, self.selenium_driver)
                break
            except (SerpException, RobotHttpException, WebDriverException, InvalidSwitchToTargetException) as err:
                self.logger.error('cannot request search engine, exception {}'.format(err))
                self.logger.debug("sleep 10 seconds and retry other search engine")
                time.sleep(10)
                self.selenium_holder.restart()
                time.sleep(5)
                self.logger.error('retry...')

        links_count = 0
        for url in serp_urls:
            link_info = TLinkInfo(TClickEngine.google, morda_url, url, anchor_text=request)
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            step_info.add_link_wrapper(link_info)
            links_count += 1
            if max_results == 1:
                break  # one  link found
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

    def export_files_to_folder(self):
        for office_info in self.offices:
            office_info.export_env.reorder_export_files_and_delete_non_declarations()
