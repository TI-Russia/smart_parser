import time

from DeclDocRecognizer.external_convertors import TExternalConverters
from common.download import TDownloadEnv
from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.conv_storage_server import TConvertStorage
from dlrobot.robot.tests.web_site_monkey import TTestEnv

from unittest import TestCase
import os
import threading


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
        time.sleep(3)
        self.assertGreater(TDownloadEnv.CONVERSION_CLIENT.all_pdf_size_sent_to_conversion, 0)
