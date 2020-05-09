import os
import logging
import sys
from robots.common.selenium_driver import TSeleniumDriver
from robots.common.find_link import TLinkInfo, TClickEngine
import argparse
import shutil

def setup_logging( logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", dest='source_url', required=True)
    parser.add_argument("--anchor", dest='anchor')
    parser.add_argument("--target", dest='target_url')
    parser.add_argument("--visible", dest='headless', default=True, action="store_false")
    parser.add_argument("--download-folder", dest='download_folder', default=None)
    return parser.parse_args()


def get_first_link(args, links):
    for e in links:
        try:
            if e.text is None:
                continue
            link_text = e.text.strip('\n\r\t ')
            if link_text.lower().startswith(args.anchor_text):
                link_info = TLinkInfo(TClickEngine.selenium, driver_holder.the_driver.current_url, None)
                driver_holder.click_element(e, link_info)
                assert driver_holder.the_driver.current_url == args.target_url
                break
        except Exception as exp:
            logger.error(exp)


def start_selenium_for_tests(args):
    if os.path.exists("geckodriver.log"):
        os.unlink("geckodriver.log")

    if args.download_folder is not None:
        if os.path.exists(args.download_folder):
            shutil.rmtree(args.download_folder, ignore_errors=True)
        os.mkdir(args.download_folder)
    try:
        driver_holder = TSeleniumDriver(headless=args.headless,
                                        download_folder=args.download_folder,
                                        loglevel="trace")
        driver_holder.start_executable()
    except Exception as exp:
        logger.error(exp)
        sys.exit(1)
    return driver_holder


if __name__ == "__main__":
    args = parse_args()
    logger = logging.getLogger("dlrobot_logger")
    setup_logging(logger, "check_selenium.log")
    driver_holder = start_selenium_for_tests(args)
    logger.info("navigate to {}\n".format(args.source_url))
    links = driver_holder.navigate_and_get_links(args.source_url)
    logger.info("Title:{}, type={}\n".format(driver_holder.the_driver.title, type(driver_holder.the_driver.title)))
    logger.info("html len: {0}".format(len(driver_holder.the_driver.page_source)))
    logger.info("links and buttons found: {0}".format(len(links)))
    if args.target_url is not None:
        get_first_link(args, links)

    driver_holder.stop_executable()