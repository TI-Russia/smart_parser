from .selenium_for_tests import TestDeclarationLinkSelenium
import os


class Kolomna1(TestDeclarationLinkSelenium):

    # this test is too unstable, because web site culture.gov.ru is unstable
    #def test_culture(self):
     #   found_links = self.download_website('web_sites/culture.gov.ru/culture.gov.ru.txt', 'https://culture.gov.ru/activities/reports/index.php')
        #self.canonize_links(found_links, 'web_sites/culture.gov.ru/found_links')
      #  self.compare_to_file(found_links, 'web_sites/culture.gov.ru/found_links')

    #def test_culture1(self):
    #    port = 10000
    #    project_path = os.path.join(os.path.dirname(__file__), 'web_sites/culture.gov.ru/project.txt')
    #    web_site_folder = os.path.join(os.path.dirname(__file__), "web_sites/culture.gov.ru/complete_save")
    #    self.setup_server(port, web_site_folder, project_path)
    #    found_links = self.download_website(project_path, 'http://127.0.0.1:{}/index.html'.format(port))
    #    #self.canonize_links(found_links, 'web_sites/culture.gov.ru/found_links')
    #    self.compare_to_file(found_links, 'web_sites/culture.gov.ru/found_links')

    def setUp(self):
        super().setUp("data.kolomnagrad1")

    def tearDown(self):
        super().tearDown()

    def test_kolomnagrad1(self):
        project_path = os.path.join(os.path.dirname(__file__), 'web_sites/kolomnagrad/project.txt')
        found_links = self.download_website(project_path, 'https://kolomnagrad.ru/docs/protivodejstvie-korrupcii/svedeniya-o-dohodah/12831-svedenija-o-dohodah-ob-imuschestve-i-objazatelstvah-imuschestvennogo-haraktera-rukovoditelej-municipalnyh-uchrezhdenij-za-2019-god.html')
        found_links = dict((k, v) for k, v in found_links.items() if k.find('svedeniya-o-dohodah') != -1)
        #self.canonize_links(found_links, 'web_sites/kolomnagrad/found_links')
        self.compare_to_file(found_links, 'web_sites/kolomnagrad/found_links')

