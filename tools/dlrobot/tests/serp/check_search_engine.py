import sys
import random
import logging
import argparse
from common.serp_parser import SearchEngine, SearchEngineEnum
from common.selenium_driver import TSeleniumDriver


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search-engine-id", dest='search_engine_id',
                        default=0, required=False, type=int)
    parser.add_argument("--headless", dest='headless', default=True, required=False)
    parser.add_argument("--site", dest='site',  required=False)
    parser.add_argument("--query", dest='query', required=False)
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
    if args.site is None:
        site = random.choice(sites)
    else:
        site = args.site
    if args.query is None:
        query = random.choice(queries)
    else:
        query = args.query
    print ("site:{} {} ".format(site, query))
    assert args.search_engine_id < SearchEngineEnum.SearchEngineCount
    urls = SearchEngine().site_search(args.search_engine_id,
                                      site,
                                      query,
                                      driver_holder,
                                      enable_cache=False,
                                          )
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
