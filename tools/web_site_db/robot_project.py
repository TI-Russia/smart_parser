from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from common.selenium_driver import TSeleniumDriver
from common.web_site_status import TWebSiteReachStatus
from common.export_files import TExportFile
from office_db.web_site_list import TDeclarationWebSiteList

import json
import shutil
import os
import tempfile
import time


class TRobotProject:
    visited_pages_extension = ".visited_pages"

    def __init__(self, logger, filename, robot_step_passports, export_folder,
                 enable_search_engine=True, start_selenium=True, web_sites_db=None):
        self.logger = logger
        self.start_time = time.time()
        self.total_timeout = 0
        self.selenium_driver = TSeleniumDriver(logger)
        self.visited_pages_file = filename + TRobotProject.visited_pages_extension
        self.click_paths_file = filename + ".click_paths"
        self.result_summary_file = filename + ".result_summary"
        if len(filename)  > 0 and not os.path.exists(self.visited_pages_file):
            shutil.copy2(filename, self.visited_pages_file)
        self.web_site_snapshots = list()
        self.robot_step_passports = robot_step_passports
        self.enable_search_engine = enable_search_engine  #switched off in tests, otherwize google shows captcha
        self.export_folder = export_folder
        self.web_sites_db = web_sites_db
        if self.web_sites_db is None:
            self.web_sites_db = TDeclarationWebSiteList(self.logger)
        self.start_selenium = start_selenium

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
        if self.start_selenium:
            self.selenium_driver.download_folder = tempfile.mkdtemp()
            self.selenium_driver.start_executable()
        return self

    def __exit__(self, type, value, traceback):
        if self.start_selenium:
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
            outf.write(json.dumps(output, ensure_ascii=False, indent=4))

    @staticmethod
    def create_project_str(main_url, regional_main_pages=[], disable_search_engine=False):
        site = {"morda_url": main_url}
        if len(regional_main_pages) > 0:
            site['regional'] = regional_main_pages

        project_content = {
            "sites": [site]
        }
        if disable_search_engine:
            project_content['disable_search_engine'] = True
        return json.dumps(project_content, indent=4, ensure_ascii=False)

    @staticmethod
    def create_project(url, file_path):
        with open(file_path, "w") as outp:
            outp.write(TRobotProject.create_project_str(
                url,
                [],
                disable_search_engine=False))
        if os.path.exists(file_path + TRobotProject.visited_pages_extension):
            os.unlink(file_path + TRobotProject.visited_pages_extension)

    @staticmethod
    def create_project_from_exported_files(logger, web_domain, file_paths, file_web_domains=None, move_files=True,
                                           project_folder=None):
        assert web_domain.find('/') == -1
        assert file_web_domains is None or len(file_web_domains) == len(file_paths)
        if project_folder is None:
            project_folder = web_domain
        if os.path.exists(project_folder):
            logger.debug("rm {}".format(project_folder))
            shutil.rmtree(project_folder, ignore_errors=True)
        os.mkdir(project_folder)
        abs_file_paths = list(os.path.abspath(x) for x in file_paths)

        logger.debug("mkdir {}".format(project_folder))
        save_dir = os.path.abspath(os.curdir)

        logger.debug("chdir {}".format(project_folder))
        os.chdir(project_folder)

        robot_project_path = os.path.join(web_domain + ".txt")
        TRobotProject.create_project(web_domain, robot_project_path)
        with TRobotProject(logger, robot_project_path, [], None, start_selenium=False) as project:
            project.add_web_site(web_domain)
            project.web_site_snapshots[0].reach_status = TWebSiteReachStatus.normal
            export_env = project.web_site_snapshots[0].export_env
            if file_web_domains is None:
                file_web_domains = [web_domain] * len(abs_file_paths)
            for file_name, curr_web_domain in zip(abs_file_paths, file_web_domains):
                export_path = os.path.join("result", curr_web_domain, os.path.basename(file_name))
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                if move_files:
                    logger.debug("move {} to {}".format(file_name, export_path))
                    shutil.move(file_name, export_path)
                else:
                    logger.debug("copy {} to {}".format(file_name, export_path))
                    shutil.copy2(file_name, export_path)

                export_file = TExportFile(url=web_domain, export_path=export_path)
                export_env.exported_files.append(export_file)
            logger.info("write {} files to result folder".format(len(file_paths)))
            project.write_project()

        logger.info("chdir {}".format(save_dir))
        os.chdir(save_dir)
        return robot_project_path

    def add_web_site(self, morda_url):
        self.web_site_snapshots.append(TWebSiteCrawlSnapshot(self, morda_url=morda_url))
        return self.web_site_snapshots[-1]

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
                    self.robot_step_passports.append({'step_name': step_name})

            for o in json_dict.get('sites', []):
                web_site = TWebSiteCrawlSnapshot(self).read_from_json(o)
                self.web_site_snapshots.append(web_site)

            if "disable_search_engine" in json_dict:
                self.enable_search_engine = False

    def fetch_main_pages(self):
        for site in self.web_site_snapshots:
            site.fetch_the_main_page()

    def write_click_features(self, filename):
        self.logger.info("create {}".format(filename))
        result = []
        for web_site in self.web_site_snapshots:
            downloaded_files_count =  sum(len(v.downloaded_files) for v in web_site.url_nodes.values())
            self.logger.info("find useless nodes in {}".format(web_site.main_page_url))
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
