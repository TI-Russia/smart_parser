from dlrobot.robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
from common.http_request import THttpRequester
from dlrobot.common.robot_step import TRobotStep


class TestEnadm(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/enadm")
        THttpRequester.ENABLE_HEAD_REQUESTS = False

    def tearDown(self):
        super().tearDown()

    def test_link_speed(self):
        urls = [
            'https://enadm.ru/index.php/protivodejstvie-koruptsii/otkrytye-dannye/selsovety#ust-pitskij-selsovet-7',
            'https://enadm.ru/index.php/protivodejstvie-koruptsii/otkrytye-dannye/selsovety#ust-pitskij-selsovet-8'
        ]
        found_links = self.collect_links_selenium(urls, link_func=TRobotStep.check_anticorr_link_text, is_last_step=False)
        self.assertEqual(1, len(found_links))
