from common.download import  TDownloadEnv
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.robot_project import TRobotProject
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging

from unittest import TestCase
import os
import urllib
import shutil
import json
import threading
import http
from functools import partial


def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        print (exp)
        pass


# it looks like mkrf has changed the site structure, so there is no income declaratiosn
# on https://www.mkrf.ru/activities/reports/index.php

class TestDeclarationLinkSelenium(TestCase):

    def setup_server(self, port, web_site_folder, project_path):
        project = TRobotProject.create_project_str("http://127.0.0.1:{}".format(port),
                                                   disable_search_engine=True, disable_selenium=False)
        with open(project_path, "w") as outp:
            outp.write(project)
        assert os.path.exists(web_site_folder)
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=web_site_folder)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        threading.Thread(target=start_server, args=(self.web_site,)).start()

    def download_website(self, project_path, start_url):

        TDownloadEnv.clear_cache_folder()
        robot_steps = [
            {
                'step_name': "declarations",
                'enable_selenium': True,
                'use_urllib': False
            }
        ]
        with TRobotProject(self.logger, project_path, robot_steps, "result", enable_search_engine=False,
                           enable_selenium=True) as project:
            project.read_project()
            office_info = project.web_site_snapshots[0]
            office_info.create_export_folder()
            office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

            step_info = TRobotStep(office_info, **robot_steps[0])
            step_info.pages_to_process[start_url] = 0
            step_info.processed_pages = set()
            step_info.apply_function_to_links(TRobotStep.looks_like_a_declaration_link)
            links = dict()
            for url,weight in step_info.step_urls.items():
                u = list(urllib.parse.urlparse(url))
                u[1] = "dummy"
                links[urllib.parse.urlunparse(u)] = weight

            for url_info in office_info.url_nodes.values():
                for d in url_info.downloaded_files:
                    links[d.downloaded_file] = 1
            return links

    def setUp(self):
        TRobotStep.check_local_address = True
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.declaration_link_selenium")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        THttpRequester.ENABLE = False
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        if hasattr(self, "web_site") and self.web_site is not None:
            self.web_site.shutdown()
        close_logger(self.logger)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        TRobotStep.check_local_address = False

    def compare_to_file(self, links, file_name):
        self.maxDiff = None
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            canon_dict = json.load(inp)
            self.assertDictEqual(canon_dict, links)

    def canonize_links(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name), "w") as outp:
            json.dump(links, outp, indent=4)

    # this test is too unstable, because web site culture.gov.ru is unstable
    #def test_culture(self):
     #   found_links = self.download_website('web_sites/culture.gov.ru/culture.gov.ru.txt', 'https://culture.gov.ru/activities/reports/index.php')
        #self.canonize_links(found_links, 'web_sites/culture.gov.ru/found_links')
      #  self.compare_to_file(found_links, 'web_sites/culture.gov.ru/found_links')

    #def test_culture1(self):
    #    port = 10000
    #    project_path = os.path.join(os.path.dirname(__file__), 'web_sites/culture.gov.ru/project.txt')
    #    web_site_folder = os.path.join(os.path.dirname(__file__), "web_sites/culture.gov.ru/complete_save")
    #    self.setup_server(port, web_site_folder, project_path)
    #    found_links = self.download_website(project_path, 'http://127.0.0.1:{}/index.html'.format(port))
    #    #self.canonize_links(found_links, 'web_sites/culture.gov.ru/found_links')
    #    self.compare_to_file(found_links, 'web_sites/culture.gov.ru/found_links')

    def test_kolomnagrad(self):
        project_path = os.path.join(os.path.dirname(__file__), 'web_sites/kolomnagrad/project.txt')
        found_links = self.download_website(project_path, 'https://kolomnagrad.ru/docs/protivodejstvie-korrupcii/svedeniya-o-dohodah/12831-svedenija-o-dohodah-ob-imuschestve-i-objazatelstvah-imuschestvennogo-haraktera-rukovoditelej-municipalnyh-uchrezhdenij-za-2019-god.html')
        found_links = dict((k, v) for k, v in found_links.items() if k.find('svedeniya-o-dohodah') != -1)
        #self.canonize_links(found_links, 'web_sites/kolomnagrad/found_links')
        self.compare_to_file(found_links, 'web_sites/kolomnagrad/found_links')

    def test_kolomnagrad1(self):
        project_path = os.path.join(os.path.dirname(__file__), 'web_sites/kolomnagrad1/project.txt')
        found_links = self.download_website(project_path, 'https://kolomnagrad.ru/index.php?do=download&id=3005')
        found_links = dict((k,v) for k, v in found_links.items() if k.find('svedeniya-o-dohodah') != -1)
        #self.canonize_links(found_links, 'web_sites/kolomnagrad1/found_links')
        self.compare_to_file(found_links, 'web_sites/kolomnagrad1/found_links')
