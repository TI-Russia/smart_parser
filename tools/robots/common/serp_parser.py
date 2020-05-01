import urllib.parse
import json
import sys
import time
import os
import random
from unidecode import unidecode
from robots.common.download import TDownloadEnv
from selenium.webdriver.common.keys import Keys
from robots.common.primitives import get_site_domain_wo_www

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/ 58.0.3029.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 YaBrowser/20.2.0.1043 Yowser/2.5 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 YaBrowser/19.12.3.320 Yowser/2.5 Safari/537.36"
]
SEARCH_URLS = [
    "https://google.com/search",
    "https://google.ru/search",
    "https://google.nl/search"
]

ACCEPT_LANGUAGES = [
    "ru-RU, ru;q=0.5",
    "en-US,en;q=0.5"
]
RESULT_SELECTOR = ".srg .g .rc .r a"

REQUEST_CACHE_FOLDER = os.path.join(TDownloadEnv.FILE_CACHE_FOLDER, "search_engine_requests")
if not os.path.exists(REQUEST_CACHE_FOLDER):
    os.makedirs(REQUEST_CACHE_FOLDER)


class GoogleSearch:

    @staticmethod
    def _request_urllib(url):
        opener = urllib.parse.build_opener()
        opener.addheaders = [
            ('User-Agent', random.choice(USER_AGENTS)),
            ("Accept-Language", random.choice(ACCEPT_LANGUAGES))
        ]
        response = opener.open(url)
        html = response.read().decode('utf8')
        response.close()
        return html

    @staticmethod
    def _request_selenium(url, driver_holder):
        driver_holder.navigate(url)
        time.sleep(6)
        return driver_holder.the_driver.page_source

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
        filename = GoogleSearch.get_cached_file_name(site_url,  query)
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
    def write_cache(site_url,  query, urls):
        filename = GoogleSearch.get_cached_file_name(site_url, query)
        cache = {
            'urls': urls,
            'site': site_url,
            'query': query,
        }
        try:
            with open(filename, "w", encoding="utf8") as outp:
                json.dump(cache, outp, ensure_ascii=False, indent=4)
        except IOError as err:
            sys.stderr("cannot write file {}".format(filename))
            pass


    @staticmethod
    def site_search(site_url, query, selenium_holder, enable_cache=True):
        if enable_cache:
            cached_results = GoogleSearch.read_cache(site_url, query)
            if len(cached_results) > 0:
                return cached_results['urls']
        assert get_site_domain_wo_www(site_url) == site_url
        request_parts = ["site:{}".format(site_url), query]
        random.shuffle(request_parts)  # more random
        site_req = " ".join(request_parts)

        GoogleSearch._request_selenium(random.choice(SEARCH_URLS), selenium_holder)
        time.sleep(4)
        element = selenium_holder.the_driver.switch_to.active_element
        element.send_keys(site_req)
        time.sleep(1)
        element.send_keys(Keys.RETURN)
        time.sleep(6)
        if "google" in query or "google" in site_url:
            print("Warning! we use keyword 'google' to filter results out, search would yield no results")
        site_search_results = []
        search_results_count = 0
        elements = list()
        for element in selenium_holder.the_driver.find_elements_by_tag_name("a"):
            url = element.get_attribute("href")
            search_results_count += 1
            if url is not None and 'google' not in url and url != '#' and url.startswith('http'):
                curr_site = get_site_domain_wo_www(url)
                if curr_site.lower() == site_url.lower():
                    site_search_results.append(url)
                    elements.append (element)

        if enable_cache:
            if search_results_count > 0:
                GoogleSearch.write_cache(site_url, query, site_search_results)

        #click on a serp item to make google happy
        if len(elements) > 0:
            random.choice(elements).click()

        return site_search_results

#urls = GoogleSearch().search("site:arshush.ru противодействие коррупции")
#for url in urls:
#    print(url)