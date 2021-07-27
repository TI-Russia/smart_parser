from dl_robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
import os


class GorSovet_Podolsk(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/gorsovet-podolsk")

    def tearDown(self):
        super().tearDown()

    def test_gorsovet_podolsk(self):
        found_links = self.collect_links_selenium('https://www.gorsovet-podolsk.ru/otchety#mm-4')
        self.assertGreater(len(found_links), 10)

