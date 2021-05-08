from dl_robot.dlrobot import TDlrobot
from DeclDocRecognizer.external_convertors import TExternalConverters
from common.download import TDownloadEnv
from common.logging_wrapper import close_logger
from web_site_db.robot_project import TRobotProject
from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.conv_storage_server import TConvertStorage

from unittest import TestCase
import os
import threading
import shutil
from datetime import datetime
import http.server
from functools import partial
from common.primitives import is_local_http_port_free


def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        pass


class TTestEnv:

    def __init__(self, port, website_folder, regional_main_pages=[]):
        self.dlrobot = None
        self.dlrobot_project = None
        self.web_site_folder = os.path.join(os.path.dirname(__file__), website_folder)
        name = os.path.basename(website_folder)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))
        self.dlrobot_result_folder = os.path.join(self.data_folder, "result")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        handler = partial(http.server.SimpleHTTPRequestHandler,
                          directory=self.web_site_folder)
        assert is_local_http_port_free(port)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        self.project_path = os.path.join(self.data_folder, "project.txt")
        regional = list("http://127.0.0.1:{}/{}".format(port, url) for url in regional_main_pages)

        project = TRobotProject.create_project_str("http://127.0.0.1:{}".format(port),
                                                   regional_main_pages=regional,
                                                   disable_search_engine=True, disable_selenium=False)
        with open(self.project_path, "w") as outp:
            outp.write(project)



    def start_server_and_robot(self, crawling_timeout=None):
        threading.Thread(target=start_server, args=(self.web_site,)).start()
        dlrobot_args = ['--clear-cache-folder',  '--project', self.project_path]
        if crawling_timeout is not None:
            dlrobot_args.extend(['--crawling-timeout', str(crawling_timeout)])
        self.dlrobot = TDlrobot(TDlrobot.parse_args(dlrobot_args))
        self.dlrobot_project =  self.dlrobot.open_project()

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
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_simple(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestArchive(TestCase):
    web_site_port = 8191

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/archives")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_archive(self):
        self.assertEqual(len(self.env.get_result_files()), 4)


class TestWebSiteWithPdf(TestCase):
    web_site_port = 8192

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/pdf")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        self.assertEqual(len(self.env.get_result_files()), 1)


class TestRandomPdf(TestCase):
    web_site_port = 8193
    conv_server_port = 8196

    def setUp(self):
        self.conv_server_address = "localhost:{}".format(self.conv_server_port)
        save_declarator_conv_url = os.environ['DECLARATOR_CONV_URL']
        os.environ['DECLARATOR_CONV_URL'] = self.conv_server_address
        self.env = TTestEnv(self.web_site_port, "web_sites/random_pdf")
        txt_file = os.path.join(self.env.web_site_folder, "random.txt")
        pdf_file = os.path.join(self.env.web_site_folder, "random.pdf")
        with open(txt_file, "w") as outp:
            outp.write(str(datetime.now()))
        converters = TExternalConverters()
        converters.convert_to_pdf(txt_file, pdf_file)
        assert os.path.exists(pdf_file)
        conv_project = os.path.join(self.env.data_folder, "conv.json")
        TConvertStorage.create_empty_db("db_input_files", "db_converted_files", conv_project)


        conv_server_args = [
            '--server-address', self.conv_server_address,
            '--use-abiword',
            '--disable-winword',
            '--disable-killing-winword',
            '--db-json', conv_project
        ]
        self.conv_server = TConvertProcessor(TConvertProcessor.parse_args(conv_server_args))

        def start_conv_server(server):
            server.start_http_server()
        self.conv_server_thread = threading.Thread(target=start_conv_server, args=(self.conv_server,))
        self.conv_server_thread.start()

        self.env.start_server_and_robot()

        os.environ['DECLARATOR_CONV_URL'] = save_declarator_conv_url

    def tearDown(self):
        self.conv_server.stop_http_server()
        self.conv_server_thread.join(1)
        self.env.tearDown()

    def test_pdf(self):
        self.assertEqual(len(self.env.get_result_files()), 0)
        self.assertGreater(TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion, 0)


class TestDownloadWithJs(TestCase):
    web_site_port = 8197

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/mkrf2")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js1(self):
        self.assertEqual (len(self.env.get_result_files()), 2)


class TestWebsiteWithJs(TestCase):
    web_site_port = 8203

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/website_with_js")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js2(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestRegional(TestCase):
    web_site_port = 8199

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/with_regional", regional_main_pages=["magadan.html"])
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_regional(self):
        self.assertEqual(2, len(self.env.get_result_files()))


class TestCrawlingTimeout(TestCase):
    web_site_port = 8204

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/simple")
        self.env.start_server_and_robot(crawling_timeout=1)

    def tearDown(self):
        self.env.tearDown()

    def test_timeout(self):
        self.assertTrue(self.env.dlrobot_project.web_site_snapshots[0].stopped_by_timeout)
        self.assertEqual(len(self.env.get_result_files()), 0)
