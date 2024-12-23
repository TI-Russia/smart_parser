from common.http_request import THttpRequester
from common.download import TDownloadEnv
from common.logging_wrapper import setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv

from unittest import TestCase


class TestVideo(TestCase):

    def setUp(self):
        self.env = TestDlrobotEnv("data.video")

        TDownloadEnv.clear_cache_folder()
        THttpRequester.ENABLE = False
        logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(logger)

    def tearDown(self):
        self.env.delete_temp_folder()

    def test_423mb_video(self):
        url = "https://epp.genproc.gov.ru/documents/1664002/25630699/%D0%AD%D1%81%D1%82%D0%B0%D1%84%D0%B5%D1%82%D0%B0%2B%D0%B4%D0%BE%D0%B1%D1%80%D1%8B%D1%85%2B%D0%B4%D0%B5%D0%BB.mp4/08c1ddfb-c48f-8c7f-9c2e-f0c66363c393?version=1.10&t=1608287244923&download=true"
        normal_url, headers, data = THttpRequester.make_http_request(url, "GET")
        self.assertEqual(0, len(data))

        normal_url, headers, data = THttpRequester.make_http_request(url, "HEAD")
        self.assertEqual(0, len(data))

    def test_video(self):
        url = "https://www.w3schools.com/html/mov_bbb.mp4"
        normal_url, headers, data = THttpRequester.make_http_request(url, "GET")
        self.assertEqual(0, len(data))




