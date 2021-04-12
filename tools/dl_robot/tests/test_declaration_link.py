from common.download import TDownloadEnv
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.robot_project import TRobotProject
from dl_robot.declaration_link import looks_like_a_declaration_link
from common.http_request import TRequestPolicy
from common.simple_logger import close_logger

import http.server
from unittest import TestCase
import time
import os
import urllib
import threading
import logging
import shutil


class THttpServerHandler(http.server.BaseHTTPRequestHandler):
    SVED_URL_PATH = '/sved.html'

    def build_headers(self, content_type="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def do_GET(self):
        self.build_headers()
        if self.path == self.SVED_URL_PATH:
            with open(self.server.test_file_path, "r", encoding="utf8") as inp:
                self.wfile.write(inp.read().encode('utf8'))
        else:
            self.wfile.write("some text".encode('utf8'))

    def do_HEAD(self):
        if self.path.endswith('.docx'):
            self.build_headers("application/vnd.openxmlformats-officedocument")
        elif self.path.endswith('.doc'):
            self.build_headers("application/msword")
        else:
            self.build_headers()


def start_server(server):
    server.serve_forever()


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


class TestHTTPServer(http.server.HTTPServer):
    def __init__(self, port):
        self.test_file_path = None
        super().__init__(('127.0.0.1', int(port)), THttpServerHandler)


class TestDeclarationLink(TestCase):
    web_site_port = 8195

    def build_url(self, path):
        return 'http://127.0.0.1:{}{}'.format(self.web_site_port, path)

    def download_website(self, file_path, use_selenium):
        self.web_server.test_file_path = os.path.join(os.path.dirname(__file__), file_path)
        assert os.path.exists(self.web_server.test_file_path)
        TDownloadEnv.clear_cache_folder()
        start_url = self.build_url(THttpServerHandler.SVED_URL_PATH)
        robot_steps = [
            {
                'step_name': "declarations",
                'check_link_func': looks_like_a_declaration_link,
                'fallback_to_selenium': use_selenium
            }
        ]
        with TRobotProject(self.logger, self.project_path, robot_steps, "result", enable_search_engine=False,
                           enable_selenium=use_selenium) as project:
            project.add_office(self.server_address)
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
        self.server_address = '127.0.0.1:{}'.format(self.web_site_port)
        self.web_server = TestHTTPServer(self.web_site_port)
        threading.Thread(target=start_server, args=(self.web_server,)).start()
        time.sleep(1)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.declaration_link")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        TRequestPolicy.ENABLE = False
        TDownloadEnv.clear_cache_folder()
        self.logger = setup_logging("dlrobot.log")
        self.project_path = os.path.join(self.data_folder, "project.txt")
        TRobotProject.create_project("http://127.0.0.1:{}".format(self.web_site_port), self.project_path)

    def tearDown(self):
        self.web_server.shutdown()
        close_logger(self.logger)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def compare_to_file(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            lines = list (l.strip() for l in inp)
            self.assertSequenceEqual(links, lines)

    def test_akrvo(self):
        links = self.download_website("web_sites/arkvo/sved.html", False)
        self.compare_to_file(links, 'web_sites/arkvo/found_links')

    def test_page_text(self):
        links = self.download_website("web_sites/page_text/sved.html", False)
        self.compare_to_file(links, 'web_sites/page_text/found_links')

    def test_other_website(self):
        links = self.download_website("web_sites/other_website/sved.html", False)
        self.compare_to_file(links, 'web_sites/other_website/found_links')

    def test_simple_doc(self):
        links = self.download_website("web_sites/simple_doc/sved.html", False)
        self.compare_to_file(links, 'web_sites/simple_doc/found_links')

    def test_admkrsk(self):
        links = self.download_website("web_sites/admkrsk/sved.html", False)
        self.compare_to_file(links, 'web_sites/admkrsk/found_links')
