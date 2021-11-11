from common.http_request import THttpRequester
from common.download import TDownloadEnv
from common.logging_wrapper import setup_logging

from unittest import TestCase
import shutil
import os


# test for THttpRequester.SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1') in http_request.py
class TestSSL(TestCase):

    def setUp(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.ssl")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        TDownloadEnv.clear_cache_folder()
        THttpRequester.ENABLE = False
        logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(logger)

    def tearDown(self):
        shutil.rmtree(self.data_folder, ignore_errors=True)

    def test_ssl(self):
        sites = ["http://www.yandex.ru", "http://chukotka.sledcom.ru/", "http://www.aot.ru",
                 "http://officefinder.rs", "http://ozerny.ru", "http://ksl.spb.sudrf.ru",  "http://spbogdo.ru",
                 "http://akrvo.ru", "http://primorie.fas.gov.ru"]
        for site in sites:
            THttpRequester.make_http_request(site, "GET")  # no exceptions



