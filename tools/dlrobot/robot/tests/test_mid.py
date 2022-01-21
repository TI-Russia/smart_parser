from dlrobot.robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
from common.http_request import THttpRequester
from common.link_info import TLinkInfo, TClickEngine
from dlrobot.common.robot_step import TRobotStep
from dlrobot.common.robot_config import TRobotConfig

class TestMid(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/mid")

    def tearDown(self):
        super().tearDown()

    def test_mid_document(self):
        THttpRequester.ENABLE_HEAD_REQUESTS = False
        url = 'https://www.mid.ru/ru/activity/corruption/svedeniya_o_dokhodakh_raskhodakh_ob_imushchestve_i_obyazatelstvakh_imushchestvennogo_kharaktera/1422852/'
        found_links = self.collect_links_selenium(url, is_last_step=True)
        self.assertGreater(len(found_links), 0)
        downloaded_files = list(k for k in found_links.keys() if k.find('document') != -1)
        self.assertGreater(len(downloaded_files), 0)

    def test_mid_video(self):
        THttpRequester.ENABLE_HEAD_REQUESTS = True
        link_info = TLinkInfo(TClickEngine.selenium,
            source_url='https://www.mid.ru/ru/brifingi/-/asset_publisher/MCZ7HQuMdqBY/content/id/4781270#12',
            target_url='https://www.mid.ru/documents/10180/4780294/210610%281%29.mp4/8acd221f-cb28-4522-a251-5437b160672e'
        )
        logger = self.logger

        class TDummyProject:
            def __init__(self):
                self.config = TRobotConfig.read_by_config_type("prod")

        class TDummyOffice:
            def __init__(self):
                self.logger = logger
                self.parent_project = TDummyProject()

        step_info = TRobotStep(TDummyOffice())
        res = step_info.normalize_and_check_link(link_info, TRobotStep.looks_like_a_declaration_link)
        self.assertFalse(res)
