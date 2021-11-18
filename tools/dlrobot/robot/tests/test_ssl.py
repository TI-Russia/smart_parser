from common.http_request import THttpRequester
from common.download import TDownloadEnv
from common.logging_wrapper import setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv

from unittest import TestCase


# test for THttpRequester.SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1') in http_request.py
class TestSSL(TestCase):

    def setUp(self):
        self.env = TestDlrobotEnv("data.ssl")

        TDownloadEnv.clear_cache_folder()
        THttpRequester.ENABLE = False
        logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(logger)

    def tearDown(self):
        self.env.delete_temp_folder()

    def test_ssl(self):
        sites = ["http://www.yandex.ru", "http://chukotka.sledcom.ru/", "http://www.aot.ru",
                 "http://officefinder.rs", "http://ozerny.ru", "http://ksl.spb.sudrf.ru",  "http://spbogdo.ru",
                 "http://akrvo.ru", "http://primorie.fas.gov.ru"]
        for site in sites:
            THttpRequester.make_http_request(site, "GET")  # no exceptions



