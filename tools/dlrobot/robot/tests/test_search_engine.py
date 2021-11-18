from common.serp_parser import SearchEngine, SearchEngineEnum
from common.selenium_driver import TSeleniumDriver

import random
import logging
from unittest import TestCase
import shutil
import os


class TestSimple(TestCase):

    def setUp(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.search_engine")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)

        self.driver_holder = TSeleniumDriver(logging, headless=True)
        self.driver_holder.start_executable()

    def tearDown(self):
        self.driver_holder.stop_executable()
        if os.environ.get("DEBUG_TESTS") is None:
            shutil.rmtree(self.data_folder, ignore_errors=True)

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
