from common.download import  TDownloadEnv
from dlrobot.common.robot_step import TRobotStep, TUrlInfo
from dlrobot.common.robot_project import TRobotProject
from dlrobot.common.robot_config import TRobotConfig
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv

import os
import urllib
import shutil
import json
from unittest import TestCase


class TestDeclarationLinkSelenium(TestCase):

    def collect_links_selenium(self, start_url, link_func=TRobotStep.looks_like_a_declaration_link,
                               is_last_step=False):

        TDownloadEnv.clear_cache_folder()
        robot_steps = [{'step_name': "declarations"}]
        with TRobotProject(self.logger, "project.txt", TRobotConfig(passport_steps=robot_steps), "result", enable_search_engine=False,
                           ) as project:
            project.read_project()
            office_info = project.web_site_snapshots[0]
            office_info.create_export_folder()

            step_info = TRobotStep(office_info, step_name="declarations", is_last_step=is_last_step)
            if isinstance(start_url, list):
                for x in start_url:
                    step_info.pages_to_process[x] = 0
                    office_info.url_nodes[x] = TUrlInfo(title="", step_name=None)
            else:
                office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)
                step_info.pages_to_process[start_url] = 0

            step_info.processed_pages = set()
            step_info.apply_function_to_links(link_func)
            links = dict()
            for url, weight in step_info.url_to_weight.items():
                u = list(urllib.parse.urlparse(url))
                u[1] = "dummy"
                links[urllib.parse.urlunparse(u)] = weight

            for url_info in office_info.url_nodes.values():
                for d in url_info.downloaded_files:
                    links[d.downloaded_file] = 1
            return links

    def setUp(self, website_folder):
        self.env = TestDlrobotEnv("data.{}".format(os.path.basename(website_folder)))
        shutil.copy2(os.path.join(os.path.dirname(__file__), website_folder, "project.txt"), self.env.data_folder)
        THttpRequester.ENABLE = False
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        if hasattr(self, "web_site") and self.web_site is not None:
            self.web_site.shutdown()
        close_logger(self.logger)
        self.env.delete_temp_folder()
        TRobotStep.check_local_address = False

    def compare_to_file(self, links, file_name):
        self.maxDiff = None
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            canon_dict = json.load(inp)
            self.assertDictEqual(canon_dict, links)

    def canonize_links(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name), "w") as outp:
            json.dump(links, outp, indent=4)

