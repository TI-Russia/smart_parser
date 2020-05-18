import urllib.parse
import json
from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
import time
import os
import random
from unidecode import unidecode
from robots.common.download import TDownloadEnv
from selenium.webdriver.common.keys import Keys
from robots.common.primitives import get_site_domain_wo_www
from robots.common.selenium_driver import TSeleniumDriver

GOOGLE_SEARCH_URLS = [
    "https://google.com/search",
    "https://google.ru/search",
    "https://google.nl/search"
]

YANDEX_SEARCH_URLS = [
    "https://ya.ru",
    "https://yandex.by",
    "https://yandex.ru"
]

REQUEST_CACHE_FOLDER = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, "search_engine_requests")
if not os.path.exists(REQUEST_CACHE_FOLDER):
    os.makedirs(REQUEST_CACHE_FOLDER)


class SearchEngine:

    @staticmethod
    def get_cached_file_name(site_url, query):
        filename = unidecode(site_url + " " + query)
        filename = filename.replace(' ', '_')
        filename = filename.replace('"', '_')
        filename = filename.replace(':', '_')
        filename = filename.replace('\\', '_').replace('/', '_')
        return os.path.join(REQUEST_CACHE_FOLDER, filename)


    @staticmethod
    def read_cache(site_url,  query):
        filename = SearchEngine.get_cached_file_name(site_url, query)
        try:
            if os.path.exists(filename):
                create_time = os.path.getmtime(filename)
                if time.time() - create_time > 24 * 3600:  # file is older than one day
                    os.unlink(filename)
                    return dict()

            with open(filename, "r", encoding="utf8") as inp:
                cached_results = json.load(inp)
                if len(cached_results) > 0:
                    assert cached_results['site'] == site_url
                    assert cached_results['query'] == query
                    return cached_results
                return dict()
        except (IOError, json.decoder.JSONDecodeError) as err:
            pass
        return dict()

    @staticmethod
    def _write_cache(logger, site_url,  query, urls):
        filename = SearchEngine.get_cached_file_name(site_url, query)
        cache = {
            'urls': urls,
            'site': site_url,
            'query': query,
        }
        try:
            with open(filename, "w", encoding="utf8") as outp:
                json.dump(cache, outp, ensure_ascii=False, indent=4)
        except IOError as err:
            logger.error("cannot write file {}".format(filename))
            pass

    @staticmethod
    def is_search_engine_ref(href):
        # to do: we don't need use this function, since we check if curr_site.lower() == site_url.lower():
        return ("google" in href) or ("yandex" in href)

    @staticmethod
    def get_search_engine_url(prefer_foreign_search_engine):
        if prefer_foreign_search_engine:
            return random.choice(GOOGLE_SEARCH_URLS)
        else:
            return random.choice(YANDEX_SEARCH_URLS)

    @staticmethod
    def site_search(site_url, query, selenium_holder: TSeleniumDriver,
                    enable_cache=True,
                    prefer_foreign_search_engine=True,
                    user_search_engine_url=None):
        if enable_cache:
            cached_results = SearchEngine.read_cache(site_url, query)
            if len(cached_results) > 0:
                return cached_results['urls']
        assert get_site_domain_wo_www(site_url) == site_url
        if SearchEngine.is_search_engine_ref(query) or SearchEngine.is_search_engine_ref(site_url):
            selenium_holder.logger.error("Warning! we use keyword 'google' to filter results out, search would yield no results")
        request_parts = ["site:{}".format(site_url), query]
        random.shuffle(request_parts)  # more random
        site_req = " ".join(request_parts)
        if user_search_engine_url is not None:
            search_engine_url = user_search_engine_url
        else:
            search_engine_url = SearchEngine.get_search_engine_url(prefer_foreign_search_engine)
        try:
            selenium_holder.navigate(search_engine_url)
            time.sleep(6)
        except (WebDriverException, InvalidSwitchToTargetException) as exp:
            if user_search_engine_url is not None:
                raise
            message = str(exp).strip(" \n\r")
            selenium_holder.logger.debug("got exception {}, sleep 10 seconds and retry other search engine".format(message))
            time.sleep(10)
            search_engine_url = SearchEngine.get_search_engine_url(not prefer_foreign_search_engine)
            selenium_holder.navigate(search_engine_url)
            time.sleep(10)
        element = selenium_holder.the_driver.switch_to.active_element
        element.send_keys(site_req)
        time.sleep(1)
        element.send_keys(Keys.RETURN)
        time.sleep(8)
        site_search_results = []
        search_results_count = 0
        selenium_holder.logger.debug("start reading serp")
        elements = list()
        for element in selenium_holder.the_driver.find_elements_by_tag_name("a"):
            url = element.get_attribute("href")
            search_results_count += 1
            if url is not None  and url != '#' and url.startswith('http'):
                if not SearchEngine.is_search_engine_ref(url):
                    curr_site = get_site_domain_wo_www(url)
                    if curr_site.lower() == site_url.lower():
                        if url not in site_search_results:
                            site_search_results.append(url)
                        elements.append(element)

        if enable_cache:
            if search_results_count > 0:
                SearchEngine._write_cache(selenium_holder.logger, site_url, query, site_search_results)

        #click on a serp item to make google happy
        try:
            if len(elements) > 0:
                random.choice(elements).click()
        except Exception as exp:
            selenium_holder.logger.debug("cannot click random item on serp ({}), keep going...".format(exp))

        return site_search_results
