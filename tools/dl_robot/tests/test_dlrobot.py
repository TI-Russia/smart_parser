from dl_robot.dlrobot import TDlrobot
from DeclDocRecognizer.external_convertors import TExternalConverters
from common.download import TDownloadEnv
from common.simple_logger import close_logger
from web_site_db.robot_project import TRobotProject

from unittest import TestCase
import os
import threading
import shutil
from datetime import datetime
import json
import http.server
from functools import partial


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

    def __init__(self, port, website_folder, regional_main_pages=[]):
        self.web_site = None
        self.web_site_folder = None
        name = os.path.basename(website_folder)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))
        self.dlrobot_result_folder = os.path.join(self.data_folder, "result")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        self.project_path = os.path.join(self.data_folder, "project.txt")
        regional = list("http://127.0.0.1:{}/{}".format(port, url) for url in regional_main_pages)

        project = TRobotProject.create_project_str("http://127.0.0.1:{}".format(port),
                                                   regional_main_pages=regional,
                                                   disable_search_engine=True, disable_selenium=False)
        with open(self.project_path, "w") as outp:
            outp.write(project)

        assert is_port_free(port)
        self.web_site_folder = os.path.join(os.path.dirname(__file__), website_folder)
        handler = partial(http.server.SimpleHTTPRequestHandler,
                          directory=self.web_site_folder)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        threading.Thread(target=start_server, args=(self.web_site,)).start()
        self.dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.project_path]))
        self.dlrobot.open_project()

    def tearDown(self):
        if self.web_site is not None:
            self.web_site.shutdown()
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
        TDownloadEnv.CONVERSION_CLIENT = None
        close_logger(self.dlrobot.logger)
        os.chdir(os.path.dirname(__file__))
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

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/simple")

    def tearDown(self):
        self.env.tearDown()

    def test_simple(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestArchive(TestCase):
    web_site_port = 8191

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/archives")

    def tearDown(self):
        self.env.tearDown()

    def test_archive(self):
        self.assertEqual(len(self.env.get_result_files()), 4)


class TestWebSiteWithPdf(TestCase):
    web_site_port = 8192

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/pdf")

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        self.assertEqual(len(self.env.get_result_files()), 1)


class TestRandomPdf(TestCase):
    web_site_port = 8193

    def setUp(self):
        website_folder = "web_sites/random_pdf"
        website_folder = os.path.join(os.path.dirname(__file__), website_folder)
        txt_file = os.path.join(website_folder, "random.txt")
        pdf_file = os.path.join(website_folder, "random.pdf")
        with open(txt_file, "w") as outp:
            outp.write(str(datetime.now()))
        converters = TExternalConverters()
        converters.convert_to_pdf(txt_file, pdf_file)
        assert os.path.exists(pdf_file)

        self.env = TTestEnv(self.web_site_port, website_folder)

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        self.assertEqual(len(self.env.get_result_files()), 0)
        self.assertGreater(TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion, 0)


class TestDownloadWithJs(TestCase):
    web_site_port = 8197

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/mkrf2")

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js1(self):
        self.assertEqual (len(self.env.get_result_files()), 2)


class TestWebsiteWithJs(TestCase):
    web_site_port = 8198

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/website_with_js")

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js2(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestRegional(TestCase):
    web_site_port = 8199

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/with_regional", regional_main_pages=["magadan.html"])

    def tearDown(self):
        self.env.tearDown()

    def test_regional(self):
        self.assertEqual(2, len(self.env.get_result_files()))
