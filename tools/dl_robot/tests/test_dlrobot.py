from DeclDocRecognizer.external_convertors import TExternalConverters
from common.download import TDownloadEnv
from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.conv_storage_server import TConvertStorage
from dl_robot.tests.web_site_monkey import TTestEnv

from unittest import TestCase
import os
import threading


class TestSimple(TestCase):
    web_site_port = 8190

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/simple")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_one_document(self):
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
        random_pdf_folder = os.path.join( os.path.dirname(__file__), "web_sites/random_pdf")
        random_pdf_file = os.path.join(random_pdf_folder, "random.pdf")
        TExternalConverters().build_random_pdf(random_pdf_file)
        self.env = TTestEnv(self.web_site_port, random_pdf_folder)
        conv_project = os.path.join(self.env.data_folder, "conv.json")
        TConvertStorage.create_empty_db("db_input_files", "db_converted_files", conv_project)

        conv_server_args = [
            '--server-address', self.conv_server_address,
            '--use-abiword',
            '--disable-winword',
            '--disable-telegram',
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


class TestFIOinAnchor(TestCase):
    web_site_port = 8205

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/admkrsk2")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_fio_in_anchor_text(self):
        self.assertEqual (len(self.env.get_result_files()), 1)
