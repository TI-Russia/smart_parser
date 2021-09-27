from dl_robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
from common.http_request import THttpRequester
from common.link_info import TLinkInfo, TClickEngine
from web_site_db.robot_step import TRobotStep


class TestMid(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/mid")

    def tearDown(self):
        super().tearDown()

    def test_mid_document(self):
        THttpRequester.ENABLE_HEAD_REQUESTS = False
        url = 'https://www.mid.ru/activity/corruption/incomes/-/asset_publisher/bFsmjKXYVJ9O/content/id/1276672'
        found_links = self.collect_links_selenium(url, is_last_step=True)
        downloaded_files = list(k for k in found_links.keys() if k.find('/downloads/') != -1)
        self.assertEqual(1, len(downloaded_files))

    def test_mid_video(self):
        THttpRequester.ENABLE_HEAD_REQUESTS = True
        link_info = TLinkInfo(TClickEngine.selenium,
            source_url='https://www.mid.ru/ru/brifingi/-/asset_publisher/MCZ7HQuMdqBY/content/id/4781270#12',
            target_url='https://www.mid.ru/documents/10180/4780294/210610%281%29.mp4/8acd221f-cb28-4522-a251-5437b160672e'
        )
        logger = self.logger
        class TDummyOffice:
            def __init__(self):
                self.logger = logger

        step_info = TRobotStep(TDummyOffice(), enable_selenium=False)
        res = step_info.normalize_and_check_link(link_info, TRobotStep.looks_like_a_declaration_link)
        self.assertFalse(res)
