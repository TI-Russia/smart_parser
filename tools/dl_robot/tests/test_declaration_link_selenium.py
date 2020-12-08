from common.download import  TDownloadEnv
from common.robot_step import TRobotStep, TUrlInfo
from common.robot_project import TRobotProject
from dl_robot.declaration_link import looks_like_a_declaration_link
from common.http_request import TRequestPolicy

from unittest import TestCase
import os
import urllib
import logging
import shutil


def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_logger")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


class TestDeclarationLinkSelenium(TestCase):

    def download_website(self, project_path, start_url):
        project_path = os.path.join(os.path.dirname(__file__), project_path)
        TDownloadEnv.clear_cache_folder()
        robot_steps = [
            {
                'step_name': "declarations",
                'check_link_func': looks_like_a_declaration_link,
                'fallback_to_selenium': True,
                'use_urllib': False
            }
        ]
        with TRobotProject(self.logger, project_path, robot_steps, "result", enable_search_engine=False,
                           enable_selenium=True) as project:
            project.read_project()
            office_info = project.offices[0]
            office_info.create_export_folder()
            office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

            step_info = TRobotStep(office_info, robot_steps[0])
            step_info.pages_to_process[start_url] = 0
            step_info.processed_pages = set()
            step_info.make_one_step()
            links = list()
            for url in step_info.step_urls:
                u = list(urllib.parse.urlparse(url))
                u[1] = "dummy"
                links.append( urllib.parse.urlunparse(u) )
            return links

    def setUp(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.declaration_link_selenium")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        TRequestPolicy.ENABLE = False
        self.logger = setup_logging("dlrobot.log")

    def tearDown(self):
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def compare_to_file(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            lines = list(l.strip() for l in inp)
            self.assertSequenceEqual(links, lines)

    def test_mkrf(self):
        links = self.download_website('web_sites/mkrf/mkrf.txt', 'https://www.mkrf.ru/activities/reports/index.php')
        self.compare_to_file(links, 'web_sites/mkrf/found_links')
