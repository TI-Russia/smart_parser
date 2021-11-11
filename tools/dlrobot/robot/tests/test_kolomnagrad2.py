from dlrobot.robot.tests.selenium_for_tests import TestDeclarationLinkSelenium


class Kolomna2(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/kolomnagrad2")

    def tearDown(self):
        super().tearDown()

    def test_kolomnagrad2(self):
        found_links = self.collect_links_selenium('https://kolomnagrad.ru/index.php?do=download&id=3005')
        found_links = dict((k, v) for k, v in found_links.items() if k.find('svedeniya-o-dohodah') != -1)
        #self.canonize_links(found_links, 'web_sites/kolomnagrad2/found_links')
        self.compare_to_file(found_links, 'web_sites/kolomnagrad2/found_links')
