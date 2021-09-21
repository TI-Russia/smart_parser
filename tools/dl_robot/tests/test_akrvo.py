from dl_robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestAkrvo(TestDeclarationLinkBase):
    web_site_port = 8401

    def setUp(self):
        super().setUp(self.web_site_port, "akrvo")

    def tearDown(self):
        super().tearDown()

    def test_akrvo(self):
        links = list(self.process_one_page("web_sites/arkvo/sved.html").keys())
        #self.canonize_links(links, 'web_sites/arkvo/found_links')
        self.compare_to_file(links, 'web_sites/arkvo/found_links')

