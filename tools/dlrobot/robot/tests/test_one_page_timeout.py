from common.http_request import THttpRequester
from dlrobot.robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestOnePageTimeout(TestDeclarationLinkBase):
    web_site_port = 8177

    def setUp(self):
        super().setUp(self.web_site_port, "one_page_timeout", timeout=2)

    def tearDown(self):
        super().tearDown()

    def test_one_page_timeout(self):
        save = THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME
        THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME = 5
        try:
            links = self.process_one_page("web_sites/one_page_timeout/sved.html")
            self.assertEqual(self.one_page_timeout_count, 1)
        finally:
            THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME = save
