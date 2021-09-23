from dl_robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestAkrvo2(TestDeclarationLinkBase):
    web_site_port = 8402

    def setUp(self):
        super().setUp(self.web_site_port, "akrvo2")

    def tearDown(self):
        super().tearDown()

    def test_2_akrvo(self):
        links = self.process_one_page("web_sites/arkvo2/parent.html")
        self.assertIn('http://dummy/25023.html', links)
        self.assertGreater(links['http://dummy/25023.html'], 40)

