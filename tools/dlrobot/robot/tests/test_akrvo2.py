from dlrobot.robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestAkrvo2(TestDeclarationLinkBase):
    web_site_port = 8402

    def setUp(self):
        super().setUp(self.web_site_port, "akrvo2")

    def tearDown(self):
        super().tearDown()

    def test_2_akrvo(self):
        links = self.process_one_page("web_sites/arkvo2/parent.html")
        self.assertEqual(2, len(links))
        self.assertGreater(links[0]['weight'], 30)

