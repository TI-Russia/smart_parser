import sys
import random
import logging
import argparse
from robots.common.serp_parser import SearchEngine
from robots.common.selenium_driver import TSeleniumDriver


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefer-russian-search-engine", dest='prefer_foreign_search_engine',
                        default=True, required=False, action="store_false")
    parser.add_argument("--headless", dest='headless', default=True, required=False)
    parser.add_argument("--search-engine-url", dest='search_engine_url', default=None, required=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        driver_holder = TSeleniumDriver(logging, headless=args.headless)
        driver_holder.start_executable()
    except Exception as exp:
        print(exp)
        sys.exit(1)

    sites = ["ru.wikipedia.org", "microsoft.com", "ru.stackoverflow.com", "news.ru"]
    queries = ["mother", "father", "virus", "windows"]
    random.seed()
    site = random.choice(sites)
    query = random.choice(queries)
    print ("site:{} {} ".format(site, query))
    urls = SearchEngine().site_search(site,
                                      query,
                                      driver_holder,
                                      enable_cache=False,
                                      prefer_foreign_search_engine=args.prefer_foreign_search_engine,
                                      user_search_engine_url=args.search_engine_url)
    print ("found urls count: {}".format(len(urls)))
    assert(len(urls) > 0)
    with open("urls.txt", "w", encoding="utf8") as out:
        for u in urls:
            out.write("{}\n".format(u))
    #assert selenium is working after google search
    links = driver_holder.navigate_and_get_links("http://aot.ru")
    assert (len(links) > 0)
    print("success")
    driver_holder.stop_executable()
    sys.exit(0)
