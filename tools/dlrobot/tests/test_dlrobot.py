from dlrobot.dlrobot import TDlrobot
from DeclDocRecognizer.external_convertors import TExternalConverters
from unittest import TestCase
import os
import threading
import shutil
import time
from datetime import datetime
import json
import http.server
from functools import partial
from common.download import TDownloadEnv

def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        pass


def is_port_free(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


class TTestEnv:

    def __init__(self, name, project):
        self.web_site = None
        self.web_site_folder = None
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))
        self.dlrobot_result_folder = os.path.join(self.data_folder, "result")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        if project is not None:
            self.project_path = os.path.join(self.data_folder, "project.txt")
            with open(self.project_path, "w") as outp:
                json.dump(project, outp)
        else:
            self.project_path = None

    def setup_website(self, port, folder):
        assert is_port_free(port)
        self.web_site_folder = os.path.join(os.path.dirname(__file__), folder)
        handler = partial(http.server.SimpleHTTPRequestHandler,
                          directory=self.web_site_folder)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        threading.Thread(target=start_server, args=(self.web_site,)).start()

    def tearDown(self):
        if self.web_site is not None:
            self.web_site.shutdown()
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def get_result_files(self):
        files = list()
        with os.scandir(self.dlrobot_result_folder) as it1:
            for entry1 in it1:
                if entry1.is_dir():
                    with os.scandir(entry1.path) as it2:
                        for entry2 in it2:
                            if entry2.is_file():
                                files.append(entry2.path)
        return files


class TestSimple(TestCase):
    web_site_port = 8190
    data_folder = "simple"

    def setUp(self):
        project = {"sites": [{"morda_url": "http://127.0.0.1:{}".format(self.web_site_port)}], "disable_search_engine": True}
        self.env = TTestEnv(self.data_folder, project)
        self.env.setup_website(self.web_site_port, "simple_website")

    def tearDown(self):
        self.env.tearDown()

    def test_simple(self):
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.env.project_path]))
        dlrobot.open_project()
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestArchive(TestCase):
    web_site_port = 8191
    data_folder = "archive"

    def setUp(self):
        project = {"sites": [{"morda_url": "http://127.0.0.1:{}".format(self.web_site_port)}], "disable_search_engine": True}
        self.env = TTestEnv(self.data_folder, project)
        self.env.setup_website(self.web_site_port, "web_site_with_archives")

    def tearDown(self):
        self.env.tearDown()

    def test_archive(self):
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.env.project_path]))
        dlrobot.open_project()
        self.assertEqual(len(self.env.get_result_files()), 4)


class TestWebSiteWithPdf(TestCase):
    web_site_port = 8192
    data_folder = "pdf"

    def setUp(self):
        project = {"sites": [{"morda_url": "http://127.0.0.1:{}".format(self.web_site_port)}], "disable_search_engine": True}
        self.env = TTestEnv(self.data_folder, project)
        self.env.setup_website(self.web_site_port, "web_site_with_pdf")

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.env.project_path]))
        dlrobot.open_project()
        self.assertEqual(len(self.env.get_result_files()), 1)


class TestRandomPdf(TestCase):
    web_site_port = 8193
    data_folder = "random_pdf"

    def setUp(self):
        project = {"sites": [{"morda_url": "http://127.0.0.1:{}".format(self.web_site_port)}], "disable_search_engine": True}
        self.env = TTestEnv(self.data_folder, project)
        self.env.setup_website(self.web_site_port, "web_site_random_pdf")

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        txt_file = os.path.join(self.env.web_site_folder, "random.txt")
        pdf_file = os.path.join(self.env.web_site_folder, "random.pdf")
        with open (txt_file, "w") as outp:
            outp.write(str(datetime.now()))
        converters = TExternalConverters()
        converters.convert_to_pdf(txt_file, pdf_file)
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.env.project_path]))
        dlrobot.open_project()
        self.assertEqual(len(self.env.get_result_files()), 0)
        self.assertGreater(TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion, 0)