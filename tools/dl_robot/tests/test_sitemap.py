from DeclDocRecognizer.external_convertors import TExternalConverters
from common.download import TDownloadEnv
from ConvStorage.conv_storage_server import TConvertProcessor
from ConvStorage.conv_storage_server import TConvertStorage
from .web_site_monkey import TTestEnv

from unittest import TestCase
import os
import threading


class TestSitemap(TestCase):
    web_site_port = 8250

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/sitemap")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_sitemap(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


