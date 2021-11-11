from dlrobot.robot.tests.declaration_link_for_tests import TestDeclarationLinkBase


class TestDuma39(TestDeclarationLinkBase):
    web_site_port = 8399

    def setUp(self):
        super().setUp(self.web_site_port, "duma39")

    def tearDown(self):
        super().tearDown()

    def test_duma39(self):
        links = self.process_one_page("web_sites/duma39/parent.html")
        self.assertEqual(1, len(links))
        self.assertGreater(links[0]['weight'], 40)

