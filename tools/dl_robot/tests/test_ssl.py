from common.http_request import make_http_request
import logging
from common.http_request import TRequestPolicy
from common.download import TDownloadEnv
from unittest import TestCase
import shutil
import os

# test for TRequestPolicy.SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1') in http_request.py

class TestSSL(TestCase):

    def setUp(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.ssl")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        TDownloadEnv.clear_cache_folder()
        TRequestPolicy.ENABLE = False

    def tearDown(self):
        shutil.rmtree(self.data_folder, ignore_errors=True)

    def test_ssl(self):
        sites = ["http://www.yandex.ru", "http://chukotka.sledcom.ru/", "http://www.aot.ru", "http://www.mid.ru",
                 "http://officefinder.rs", "http://ozerny.ru", "http://ksl.spb.sudrf.ru",  "http://spbogdo.ru",
                 "http://akrvo.ru", "http://primorie.fas.gov.ru"]
        for site in sites:
            make_http_request(logging, site, "GET") # no exceptions



