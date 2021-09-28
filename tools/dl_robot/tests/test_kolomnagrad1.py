from dl_robot.tests.selenium_for_tests import TestDeclarationLinkSelenium
from common.http_request import THttpRequester


class Kolomna1(TestDeclarationLinkSelenium):

    def setUp(self):
        super().setUp("web_sites/kolomnagrad1")

    def tearDown(self):
        super().tearDown()

    def test_kolomnagrad1(self):
        THttpRequester.ENABLE_HEAD_REQUESTS = False
        found_links = self.collect_links_selenium( 'https://kolomnagrad.ru/docs/protivodejstvie-korrupcii/svedeniya-o-dohodah/12831-svedenija-o-dohodah-ob-imuschestve-i-objazatelstvah-imuschestvennogo-haraktera-rukovoditelej-municipalnyh-uchrezhdenij-za-2019-god.html')
        found_links = dict((k, v) for k, v in found_links.items() if k.find('svedeniya-o-dohodah') != -1)
        #self.canonize_links(found_links, 'web_sites/kolomnagrad1/found_links')
        self.compare_to_file(found_links, 'web_sites/kolomnagrad1/found_links')

