from common.download import TDownloadEnv
from selenium.webdriver.common.keys import Keys
from common.primitives import strip_scheme_and_query
from common.selenium_driver import TSeleniumDriver

from unidecode import unidecode
import json
import time
import os
import random
import re


class SerpException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SearchEngineEnum:
    GOOGLE = 0
    YANDEX = 1
    BING = 2
    SearchEngineCount = 3


SEARCH_URLS = {
    SearchEngineEnum.GOOGLE: [
                    "https://google.com/search",
                    "https://google.ru/search",
                    "https://google.nl/search"
             ],
    SearchEngineEnum.YANDEX: [
                    "https://ya.ru",
                    "https://yandex.by",
                    "https://yandex.ru"
              ],
    SearchEngineEnum.BING:  [
                    "https://bing.com"
             ]
}


class SearchEngine:

    @staticmethod
    def get_cached_file_name(site_url, query):
        filename = unidecode(site_url + " " + query)
        filename = re.sub('[ :"\\/]', "_", filename)
        return os.path.join(TDownloadEnv.get_search_engine_cache_folder(), filename)

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
    def _send_request(search_engine, site_url, query, selenium_holder: TSeleniumDriver):
        if SearchEngine.is_search_engine_ref(query) or SearchEngine.is_search_engine_ref(site_url):
            selenium_holder.logger.error("Warning! we use keyword 'google' to filter results out, search would yield no results")
        request_parts = ["site:{}".format(site_url), query]
        random.shuffle(request_parts)  # more random
        site_req = " ".join(request_parts)
        search_engine_url = random.choice(SEARCH_URLS[search_engine])
        selenium_holder.navigate(search_engine_url)
        time.sleep(6)
        element = selenium_holder.the_driver.switch_to.active_element
        element.send_keys(site_req)
        time.sleep(1)
        element.send_keys(Keys.RETURN)

    @staticmethod
    def _parse_serp(selenium_holder: TSeleniumDriver):
        search_results = []
        selenium_holder.logger.debug("start reading serp")
        elements = list()
        for element in selenium_holder.the_driver.find_elements_by_tag_name("a"):
            url = element.get_attribute("href")
            if url is not None and url != '#' and url.startswith('http'):
                if not SearchEngine.is_search_engine_ref(url):
                    search_results.append(url)
                    elements.append(element)

        #click on a serp item to make google happy
        try:
            if len(elements) > 0:
                random.choice(elements).click()
        except Exception as exp:
            selenium_holder.logger.debug("cannot click random item on serp ({}), keep going...".format(exp))

        return search_results

    @staticmethod
    def site_search(search_engine, site_url, query, selenium_holder: TSeleniumDriver,
                    enable_cache=True):

        if enable_cache:
            cached_results = SearchEngine.read_cache(site_url, query)
            if len(cached_results) > 0:
                return cached_results['urls']

        SearchEngine._send_request(search_engine, site_url, query, selenium_holder)

        time.sleep(8)

        search_results = SearchEngine._parse_serp(selenium_holder)
        if len(search_results) == 0:
            html = selenium_holder.the_driver.page_source
            if html.find("ничего не нашлось") == -1 or html.find("ничего не найдено") == -1 \
                or html.find('did not match any documents') == -1:
                #with open("debug_captcha.html", "w") as outp:
                #    outp.write(selenium_holder.the_driver.page_source)
                raise SerpException("no search results, look in debug_captcha.html, may be captcha")

        site_search_results = list()
        # https://www.mos.ru/dgi/ -> mos.ru/dgi
        web_site = strip_scheme_and_query(site_url)
        for url in search_results:
            if strip_scheme_and_query(url).startswith(web_site):
                if url not in site_search_results:
                    site_search_results.append(url)

        if enable_cache:
            if len(search_results) > 0:
                SearchEngine._write_cache(selenium_holder.logger, site_url, query, site_search_results)

        return site_search_results
