import os

from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", dest='use_chrome', required=False, action="store_true", default=False)
    parser.add_argument("urls", nargs="*")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    logger = setup_logging(log_file_name="check_selenium.log")
    args = parse_args()
    if os.path.exists("geckodriver.log"):
        logger.info("rm geckodriver.log")
        os.unlink("geckodriver.log")
    driver = TSeleniumDriver(logger, True, loglevel="DEBUG", start_retry_count=1, use_chrome=args.use_chrome)
    driver.start_executable()
    if len(args.urls) > 0:
        url = args.urls[0]
        if not url.startswith("http"):
            url = "http://" + url
    else:
        url = "http://www.aot.ru"
    print("navigate {}".format(url))
    driver.navigate(url)
    print("Title: {}".format(driver.the_driver.title))
    driver.stop_executable()