from dl_robot.tests.selenium_for_tests import TestDeclarationLinkSelenium


class TestMid(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/mid")

    def tearDown(self):
        super().tearDown()

    def test_mid(self):
        url = 'https://www.mid.ru/activity/corruption/incomes/-/asset_publisher/bFsmjKXYVJ9O/content/id/1276672'
        found_links = self.collect_links_selenium(url, is_last_step=True)
        downloaded_files = list(k for k in found_links.keys() if k.find('/downloads/') != -1)
        self.assertEqual(1, len(downloaded_files))
