from dlrobot.robot.tests.web_site_monkey import TTestEnv

from unittest import TestCase


class TestSimple(TestCase):
    web_site_port = 8190

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/simple")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_one_document(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestArchive(TestCase):
    web_site_port = 8191

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/archives")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_archive(self):
        self.assertEqual(len(self.env.get_result_files()), 4)


class TestWebSiteWithPdf(TestCase):
    web_site_port = 8192

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/pdf")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_pdf(self):
        self.assertEqual(len(self.env.get_result_files()), 1)


class TestDownloadWithJs(TestCase):
    web_site_port = 8197

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/mkrf2")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js1(self):
        result_files = self.env.get_result_files()
        self.assertEqual(2, len(result_files))


class TestWebsiteWithJs(TestCase):
    web_site_port = 8203

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/website_with_js")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_download_with_js2(self):
        self.assertEqual (len(self.env.get_result_files()), 1)


class TestCrawlingTimeout(TestCase):
    web_site_port = 8204

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/simple")
        self.env.start_server_and_robot(crawling_timeout=1)

    def tearDown(self):
        self.env.tearDown()

    def test_timeout(self):
        self.assertTrue(self.env.dlrobot_project.web_site_snapshots[0].stopped_by_timeout)
        self.assertEqual(len(self.env.get_result_files()), 0)


class TestFIOinAnchor(TestCase):
    web_site_port = 8205

    def setUp(self):
        self.env = TTestEnv(self.web_site_port, "web_sites/admkrsk2")
        self.env.start_server_and_robot()

    def tearDown(self):
        self.env.tearDown()

    def test_fio_in_anchor_text(self):
        self.assertEqual (len(self.env.get_result_files()), 1)
