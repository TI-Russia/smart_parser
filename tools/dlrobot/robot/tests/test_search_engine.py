from common.serp_parser import SearchEngine, SearchEngineEnum
from common.selenium_driver import TSeleniumDriver
from dlrobot.robot.tests.common_env import TestDlrobotEnv

import random
import logging
from unittest import TestCase


class TestSimple(TestCase):

    def setUp(self):
        self.env = TestDlrobotEnv("data.search_engine")
        self.driver_holder = TSeleniumDriver(logging, headless=True)
        self.driver_holder.start_executable()

    def tearDown(self):
        self.driver_holder.stop_executable()
        self.env.delete_temp_folder()

    def check_search_engine(self, search_engine_id):
        sites = ["ru.wikipedia.org", "microsoft.com", "ru.stackoverflow.com", "news.ru"]
        queries = ["mother", "father", "virus", "windows"]
        random.seed()
        site = random.choice(sites)
        query = random.choice(queries)
        print("search_engine_id={}, query={}, site={}".format(search_engine_id, query, site))
        urls = SearchEngine().site_search(search_engine_id,
                                      site,
                                      query,
                                      self.driver_holder,
                                      enable_cache=False)
        self.assertGreater(len(urls), 0)

    def test_yandex(self):
        self.check_search_engine(SearchEngineEnum.YANDEX)

    def test_google(self):
        self.check_search_engine(SearchEngineEnum.GOOGLE)

    def test_bing(self):
        self.check_search_engine(SearchEngineEnum.BING)

    def test_simple_navigate(self):
        #assert selenium is working after google search
        links = self.driver_holder.navigate_and_get_links_js("http://aot.ru")
        self.assertGreater(len(links), 0)
