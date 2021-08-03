from web_site_db.robot_step import TRobotStep
from dl_robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestDeclarationLink(TestDeclarationLinkBase):
    web_site_port = 8195

    def setUp(self):
        super().setUp(TestDeclarationLink.web_site_port, "declaration_link")

    def tearDown(self):
        super().tearDown()

    def test_page_text(self):
        links = self.process_one_page("web_sites/page_text/sved.html")
        #self.canonize_links(links, 'web_sites/page_text/found_links')
        self.compare_to_file(links, 'web_sites/page_text/found_links')

    def test_other_website(self):
        save = TRobotStep.check_local_address
        TRobotStep.check_local_address = False
        links = self.process_one_page("web_sites/other_website/sved.html")
        # self.canonize_links(links, 'web_sites/other_website/found_links')
        self.compare_to_file(links, 'web_sites/other_website/found_links')
        TRobotStep.check_local_address = save

    def test_simple_doc(self):
        links = self.process_one_page("web_sites/simple_doc/sved.html")
        # self.canonize_links(links, 'web_sites/simple_doc/found_links')
        self.compare_to_file(links, 'web_sites/simple_doc/found_links')

    def test_admkrsk(self):
        links = self.process_one_page("web_sites/admkrsk/sved.html")
        #self.canonize_links(links, 'web_sites/admkrsk/found_links')
        self.compare_to_file(links, 'web_sites/admkrsk/found_links')

    def test_rosminzdrav(self):
        links = self.process_one_page("web_sites/minzdrav/6_4_2.html")
        #self.canonize_links(links, 'web_sites/minzdrav/found_links')
        self.compare_to_file(links, 'web_sites/minzdrav/found_links')

    def test_zsro(self):
        links = self.process_one_page("web_sites/zsro/sved.html")
        #self.canonize_links(links, 'web_sites/zsro/found_links')
        self.compare_to_file(links, 'web_sites/zsro/found_links')

    def test_khabkrai(self):
        links = self.process_one_page("web_sites/khabkrai/sved.html")
        #self.canonize_links(links, 'web_sites/khabkrai/found_links')
        self.compare_to_file(links, 'web_sites/khabkrai/found_links')
