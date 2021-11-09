import os

from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging
from common.serp_parser import SearchEngineEnum, SearchEngine

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", dest='site', required=False, default="gorsovet-podolsk.ru")
    parser.add_argument("--query", dest='query', required=False, default="\"сведения о доходах\"")
    parser.add_argument("--search-engine-id", dest='search_engine_id', required=False, default=SearchEngineEnum.GOOGLE)
    parser.add_argument("urls", nargs="*")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()

    logger = setup_logging(log_file_name="check_search_engine.log")
    if os.path.exists("geckodriver.log"):
        logger.info("rm geckodriver.log")
        os.unlink("geckodriver.log")
    driver = TSeleniumDriver(logger, True, loglevel="DEBUG", start_retry_count=1)
    search_engine = SearchEngine()
    driver.start_executable()
    urls = search_engine.site_search(args.search_engine_id,
                                      args.site,
                                      args.query,
                                      driver,
                                      enable_cache=False)
    driver.stop_executable()
    for u in urls:
        print(u)