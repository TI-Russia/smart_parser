import urllib.request as urllib2
import urllib
import time
from bs4 import BeautifulSoup
from download import get_site_domain_wo_www

class GoogleSearch:
    USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/ 58.0.3029.81 Safari/537.36"
    SEARCH_URL = "https://google.com/search"
    RESULT_SELECTOR = ".srg .g .rc .r a"
    DEFAULT_HEADERS = [
        ('User-Agent', USER_AGENT),
        ("Accept-Language", "en-US,en;q=0.5"),
    ]

    @staticmethod
    def _request_urllib(url):
        opener = urllib2.build_opener()
        opener.addheaders = GoogleSearch.DEFAULT_HEADERS
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
    def site_search(site_url, query, selenium_holder, language="ru"):
        site_req = "site:{} {}".format(get_site_domain_wo_www(site_url), query)
        url = GoogleSearch.SEARCH_URL + "?q=" + urllib2.quote(site_req) + "&hl=" + language
        url += "&filter=0"
        try:
            html = GoogleSearch._request_urllib(url)
        except urllib.error.HTTPError as err:
            html = GoogleSearch._request_selenium(url, selenium_holder)

        soup = BeautifulSoup(html, "lxml")
        serp = list(soup.select(GoogleSearch.RESULT_SELECTOR))
        search_results = []
        for r in serp:
            url = r["href"]
            if 'google' not in url and url != '#' and url.startswith('http'):
                curr_site = get_site_domain_wo_www(url)
                if curr_site.lower() == site_url.lower():
                    search_results.append(url)
        return search_results


#urls = GoogleSearch().search("site:arshush.ru противодействие коррупции")
#for url in urls:
#    print(url)