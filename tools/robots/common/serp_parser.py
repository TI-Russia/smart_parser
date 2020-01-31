import urllib.request as urllib2
import urllib
import json
import sys
import time
import os
import random
from unidecode import unidecode
from bs4 import BeautifulSoup
from download import get_site_domain_wo_www, FILE_CACHE_FOLDER

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
    "https://google.de/search"
]

ACCEPT_LANGUAGES = [
    "ru-RU, ru;q=0.5",
    "en-US,en;q=0.5"
]
RESULT_SELECTOR = ".srg .g .rc .r a"

REQUEST_CACHE_FOLDER = os.path.join(FILE_CACHE_FOLDER, "search_engine_requests")
if not os.path.exists(REQUEST_CACHE_FOLDER):
    os.makedirs(REQUEST_CACHE_FOLDER)


class GoogleSearch:

    @staticmethod
    def _request_urllib(url):
        opener = urllib2.build_opener()
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
    def site_search(site_url, query, selenium_holder, language="ru"):
        cached_results = GoogleSearch.read_cache(site_url, query)
        if len(cached_results) > 0:
            return cached_results['urls']
        request_parts = ["site:{}".format(get_site_domain_wo_www(site_url)),
                         query]
        random.shuffle(request_parts) # more random
        site_req = " ".join(request_parts)
        url = random.choice(SEARCH_URLS) + "?q=" + urllib2.quote(site_req) + "&hl=" + language
        url += "&filter=0"
        try:
            html = GoogleSearch._request_urllib(url)
        except urllib.error.HTTPError as err:
            html = GoogleSearch._request_selenium(url, selenium_holder)

        soup = BeautifulSoup(html, "lxml")
        serp = list(soup.select(RESULT_SELECTOR))
        site_search_results = []
        search_results_count = 0
        for r in serp:
            url = r["href"]
            search_results_count += 1
            if 'google' not in url and url != '#' and url.startswith('http'):
                curr_site = get_site_domain_wo_www(url)
                if curr_site.lower() == site_url.lower():
                    site_search_results.append(url)

        if search_results_count > 0:
            GoogleSearch.write_cache(site_url, query, site_search_results)

        return site_search_results


#urls = GoogleSearch().search("site:arshush.ru противодействие коррупции")
#for url in urls:
#    print(url)