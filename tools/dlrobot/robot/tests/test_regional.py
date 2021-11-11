from dlrobot.robot.tests.web_site_monkey import TTestEnv
from unittest import TestCase


class TestRegional(TestCase):
    web_site_port = 8180

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/with_regional", regional_main_pages=["magadan.html"])
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_regional(self):
        self.assertEqual(2, len(self.env.get_result_files()))
