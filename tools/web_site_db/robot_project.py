from web_site_db.robot_web_site import TWebSiteCrawlSnapshot, TRobotStep
from common.selenium_driver import TSeleniumDriver
from common.link_info import TLinkInfo, TClickEngine
from common.http_request import THttpRequester

from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
import json
import shutil
import os
import tempfile
import time


class TRobotProject:

    def __init__(self, logger, filename, robot_step_passports, export_folder, enable_selenium=True, enable_search_engine=True):
        self.logger = logger
        self.start_time = time.time()
        self.total_timeout = 0
        self.selenium_driver = TSeleniumDriver(logger)
        self.visited_pages_file = filename + ".visited_pages"
        self.click_paths_file = filename + ".click_paths"
        self.result_summary_file = filename + ".result_summary"
        if not os.path.exists(self.visited_pages_file):
            shutil.copy2(filename, self.visited_pages_file)
        self.web_site_snapshots = list()
        self.robot_step_passports = robot_step_passports
        self.enable_search_engine = enable_search_engine  #switched off in tests, otherwize google shows captcha
        self.export_folder = export_folder
        self.enable_selenium = enable_selenium

    def have_time_for_last_dl_recognizer(self):
        if self.total_timeout == 0:
            return True
        future_kill_time = self.start_time + self.total_timeout
        if future_kill_time - time.time() < 60*20:
            #we need at least 20 minutes to export files
            return False
        return True

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
        with open(self.visited_pages_file, "w", encoding="utf8") as outf:
            output =  {
                'sites': [o.to_json() for o in self.web_site_snapshots],
                'step_names': self.get_robot_step_names()
            }
            if not self.enable_search_engine:
                output["disable_search_engine"] = True
            if not self.enable_selenium:
                output['disable_selenium'] = True
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    @staticmethod
    def create_project_str(main_url, regional_main_pages=[], disable_search_engine=False, disable_selenium=False):
        site = {"morda_url": main_url}
        if len(regional_main_pages) > 0:
            site['regional'] = regional_main_pages

        project_content = {
            "sites": [site]
        }
        if disable_search_engine:
            project_content['disable_search_engine'] = True
        if disable_selenium:
            project_content['disable_selenium'] = True
        return json.dumps(project_content, indent=4, ensure_ascii=False)

    @staticmethod
    def create_project(url, file_path):
        with open(file_path, "w") as outp:
            outp.write(TRobotProject.create_project_str(
                url,
                [],
                True, #disable_selinium in tests
                False))

    def add_web_site(self, morda_url):
        web_site = TWebSiteCrawlSnapshot(self)
        web_site.morda_url = morda_url
        self.web_site_snapshots.append(web_site)

    def read_project(self, check_step_names=True):
        self.web_site_snapshots = list()
        with open(self.visited_pages_file, "r", encoding="utf8") as inpf:
            json_dict = json.loads(inpf.read())
            if check_step_names:
                if 'step_names' in json_dict:
                    if json_dict['step_names'] != self.get_robot_step_names():
                        raise Exception("different step step_names, adjust manually or rebuild the project")
            else:
                self.robot_step_passports = list()
                for step_name in json_dict['step_names']:
                    self.robot_step_passports.append(step_name)

            uniq_domains = set()
            for o in json_dict.get('sites', []):
                web_site = TWebSiteCrawlSnapshot(self).read_from_json(o)

                web_domain = web_site.get_domain_name()
                assert web_domain not in uniq_domains  # do not write twice the same web domain in one project,
                                                  # since the result folder is normally the same web domain
                uniq_domains.add(web_domain)

                self.web_site_snapshots.append(web_site)

            if "disable_search_engine" in json_dict:
                self.enable_search_engine = False

            if 'disable_selenium' in json_dict:
                self.logger.debug("disable selenium")
                self.enable_selenium = False

    def fetch_main_pages(self):
        for site in self.web_site_snapshots:
            site.fetch_the_main_page()

    def write_click_features(self, filename):
        self.logger.info("create {}".format(filename))
        result = []
        for web_site in self.web_site_snapshots:
            downloaded_files_count =  sum(len(v.downloaded_files) for v in web_site.url_nodes.values())
            self.logger.info("find useless nodes in {}".format(web_site.morda_url))
            self.logger.info("all url nodes and downloaded with selenium: {}".format(
                len(web_site.url_nodes) + downloaded_files_count))
            for url, info in web_site.url_nodes.items():
                if len(info.downloaded_files) > 0:
                    for d in info.downloaded_files:
                        path = web_site.get_shortest_path_to_root(url)
                        file_info = dict(d.items())
                        file_info['url'] = 'element_index:{}. url:{}'.format(d['element_index'], url)
                        path.append(file_info)
                        result.append({
                            'dl_recognizer_result': d['dl_recognizer_result'],
                            'path': path
                        })
                elif len(info.linked_nodes) == 0:
                    path = web_site.get_path_to_root(url)
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
        for web_site in self.web_site_snapshots:
            for export_record in web_site.export_env.exported_files:
                path = web_site.get_shortest_path_to_root(export_record.url)
                rec = {
                    'click_path': path,
                    'cached_file': export_record.cached_file.replace('\\', '/'),
                    'sha256': export_record.sha256
                }
                if export_record.archive_index != -1:
                    rec['archive_index'] = export_record.archive_index
                files_with_click_path.append(rec)
        files_with_click_path.sort(key=(lambda x: x['sha256']))

        # full report
        with open(self.click_paths_file, "w", encoding="utf8") as outf:
            json.dump(files_with_click_path, outf, ensure_ascii=False, indent=4)

        unique_files = list(set(x.get('smart_parser_json_sha256', x.get('sha256')) for x in files_with_click_path))
        unique_files.sort()
        if len(unique_files) > 0:
            # short report to commit to git
            with open(self.result_summary_file, "w", encoding="utf8") as outf:
                report = {
                    "files_count": len(unique_files),
                    "files_sorted": unique_files,
                }
                json.dump(report, outf, ensure_ascii=False, indent=4)

    def export_files_to_folder(self):
        for web_site in self.web_site_snapshots:
            web_site.export_env.reorder_export_files_and_delete_non_declarations()
