from common.download import TDownloadEnv
from web_site_db.robot_step import TRobotStep, TUrlInfo
from web_site_db.robot_project import TRobotProject
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging

import http.server
from unittest import TestCase
import time
import os
import urllib
import threading
import shutil
from pathlib import Path
import json


class THttpServerHandler(http.server.BaseHTTPRequestHandler):

    def build_headers(self, content_type="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def do_GET(self):
        if self.server.timeout > 0:
            time.sleep(self.server.timeout)
        self.build_headers()
        local_file = os.path.join(self.server.web_site_folder, self.path[1:])
        #print("do_GET {}".format(local_file))
        if os.path.exists(local_file) and Path(local_file).is_file():
            with open(local_file, "r", encoding="utf8") as inp:
                self.wfile.write(inp.read().encode('utf8'))
        else:
            self.wfile.write("some text".encode('utf8'))

    def do_HEAD(self):
        if self.server.timeout > 0:
            time.sleep(self.server.timeout)
        if self.path.endswith('.docx'):
            self.build_headers("application/vnd.openxmlformats-officedocument")
        elif self.path.endswith('.doc'):
            self.build_headers("application/msword")
        else:
            self.build_headers()


def start_server(server):
    server.serve_forever()


class TestHTTPServer(http.server.HTTPServer):
    def __init__(self, port, timeout=0):
        self.web_site_folder = None
        self.timeout = timeout
        super().__init__(('127.0.0.1', int(port)), THttpServerHandler)

    def set_web_site_folder(self, folder):
        self.web_site_folder = folder


class TestDeclarationLinkBase(TestCase):

    def build_url(self, path):
        return 'http://127.0.0.1:{}{}'.format(self.web_site_port, path)

    def process_one_page(self, relative_file_path):
        self.one_page_timeout_count = 0
        file_path = os.path.join(os.path.dirname(__file__), relative_file_path)
        assert os.path.exists(file_path)
        self.web_server.set_web_site_folder(os.path.dirname(file_path))
        TDownloadEnv.clear_cache_folder()
        start_url = self.build_url('/' + os.path.basename(file_path))
        robot_steps = [
            {
                'step_name': "declarations"
            }
        ]
        with TRobotProject(self.logger, self.project_path, robot_steps, "result", enable_search_engine=False
                           ) as project:
            project.add_web_site(self.server_address)
            office_info = project.web_site_snapshots[0]
            office_info.create_export_folder()
            office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

            step_info = TRobotStep(office_info, is_last_step=True, **robot_steps[0])
            step_info.pages_to_process[start_url] = 0
            step_info.processed_pages = set()
            step_info.apply_function_to_links(TRobotStep.looks_like_a_declaration_link)
            self.one_page_timeout_count = step_info.one_page_timeout_count
            links = list()
            for url, weight in step_info.url_to_weight.items():
                u = list(urllib.parse.urlparse(url))
                u[1] = "dummy"
                anchor = office_info.url_nodes[start_url].linked_nodes[url]['text']
                links.append({'url': urllib.parse.urlunparse(u), 'weight': weight, 'anchor': anchor})
            return links

    def setUp(self, port, name, timeout=0):
        self.web_site_port = port
        TRobotStep.check_local_address = True
        self.server_address = '127.0.0.1:{}'.format(self.web_site_port)
        self.web_server = TestHTTPServer(self.web_site_port, timeout=timeout)
        self.http_server_thread = threading.Thread(target=start_server, args=(self.web_server,))
        self.http_server_thread.start()
        time.sleep(1)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data." + name)
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        THttpRequester.ENABLE = False
        TDownloadEnv.clear_cache_folder()
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)
        self.project_path = os.path.join(self.data_folder, "project.txt")
        TRobotProject.create_project("http://127.0.0.1:{}".format(self.web_site_port), self.project_path)

    def tearDown(self):
        self.web_server.shutdown()
        close_logger(self.logger)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        self.http_server_thread.join(1)
        self.web_server.server_close()
        time.sleep(1)
        TRobotStep.check_local_address = False

    def compare_to_file(self, links, file_name):
        self.maxDiff = None
        with open(os.path.join(os.path.dirname(__file__), file_name)) as inp:
            canon_links = list(json.loads(l) for l in inp)
            if canon_links != links:
                self.canonize_links(links, file_name + ".new")
            self.assertSequenceEqual(canon_links, links)

    def canonize_links(self, links, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name), "w") as outp:
            for l in links:
                outp.write(json.dumps(l, ensure_ascii=False) + "\n")
