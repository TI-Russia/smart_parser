from dlrobot.robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestAdmKrsk(TestDeclarationLinkBase):
    web_site_port = 8403

    def setUp(self):
        super().setUp(self.web_site_port, "admkrsk")

    def tearDown(self):
        super().tearDown()

    def test_admkrsk(self):
        links = self.process_one_page("web_sites/admkrsk/sved.html")
        #self.canonize_links(links, 'web_sites/admkrsk/found_links')
        self.compare_to_file(links, 'web_sites/admkrsk/found_links')

