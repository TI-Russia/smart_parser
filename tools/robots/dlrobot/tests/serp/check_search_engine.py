import sys
import random

from robots.common.serp_parser import GoogleSearch
from robots.common.selenium_driver import TSeleniumDriver

if __name__ == "__main__":
    try:
        driver_holder = TSeleniumDriver(True)
        driver_holder.start_executable()
    except Exception as exp:
        print(exp)
        sys.exit(1)

    sites = ["ru.wikipedia.org", "microsoft.com", "ru.stackoverflow.com", "news.ru"]
    queries = ["mother", "father", "yandex", "virus", "windows"]
    random.seed()
    site = random.choice(sites)
    query = random.choice(queries)
    print ("site:{} {} ".format(site, query))
    urls = GoogleSearch().site_search(site, query, driver_holder, enable_cache=False)
    print ("found urls count: {}".format(len(urls)))
    assert(len(urls) > 0)

    #assert selenium is working after google search
    links = driver_holder.navigate_and_get_links("http://aot.ru")
    assert (len(links) > 0)
    print ("success")
    sys.exit(0)