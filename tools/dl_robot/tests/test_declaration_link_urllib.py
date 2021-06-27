from common.download import  TDownloadEnv
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.robot_project import TRobotProject
from dl_robot.declaration_link import looks_like_a_declaration_link
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging

from unittest import TestCase
import os
import urllib
import shutil


class TestDeclarationLinkUrllib(TestCase):

    def download_website(self, project_path, start_url):
        project_path = os.path.join(os.path.dirname(__file__), project_path)
        TDownloadEnv.clear_cache_folder()
        robot_steps = [
            {
                'step_name': "declarations",
                'fallback_to_selenium': False,
                'use_urllib': True
            }
        ]
        with TRobotProject(self.logger, project_path, robot_steps, "result", enable_search_engine=False,
                           enable_selenium=False) as project:
            project.read_project()
            office_info = project.web_site_snapshots[0]
            office_info.check_urllib_access()
            office_info.create_export_folder()
            office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

            step_info = TRobotStep(office_info, **robot_steps[0])
            step_info.pages_to_process[start_url] = 0
            step_info.processed_pages = set()
            step_info.apply_function_to_links(looks_like_a_declaration_link)
            links = list()
            for url in step_info.step_urls:
                u = list(urllib.parse.urlparse(url))
                u[1] = "dummy"
                links.append( urllib.parse.urlunparse(u) )
            return links

    def setUp(self):
        TRobotStep.check_local_address = True
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.declaration_link_urllib")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        THttpRequester.ENABLE = False
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        close_logger(self.logger)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        TRobotStep.check_local_address = False

    def compare_to_file(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            lines = list(l.strip() for l in inp)
            self.assertSequenceEqual(lines, links)

    def canonize_links(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name), "w") as outp:
            for l in links:
                outp.write(l + "\n")

    def test_rosminzdrav_real(self):
        self.maxDiff = None
        found_links = self.download_website('web_sites/minzdrav2/minzdrav.txt', 'https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/4/2')
        #self.canonize_links(found_links, 'web_sites/minzdrav2/found_links')
        self.compare_to_file(found_links, 'web_sites/minzdrav2/found_links')

