import os
import logging
import sys
from common.selenium_driver import TSeleniumDriver
from common.find_link import TLinkInfo, TClickEngine
import argparse
import shutil


def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_logger")
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
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", dest='source_url', required=True)
    parser.add_argument("--start-anchor", dest='anchor')
    parser.add_argument("--assert-child-url", dest='assert_child_url')
    parser.add_argument("--visible", dest='headless', default=True, action="store_false")
    parser.add_argument("--download-folder", dest='download_folder', default=None)
    parser.add_argument("--check-scroll-down", dest="check_scroll_down", action="store_true", default=False)
    return parser.parse_args()


def get_links(logger, links,  start_anchor_text):
    urls =  set()
    element_index = 0
    for e in links:
        element_index += 1
        try:
            if e.text is None:
                continue
            link_text = e.text.strip('\n\r\t ')
            logger.debug("check link anchor={}, element_index={}".format(link_text, element_index))
            if link_text.lower().startswith(start_anchor_text):
                logger.debug("found link anchor={}".format(link_text))
                href = e.get_attribute('href')
                if href is None:
                    link_info = TLinkInfo(TClickEngine.selenium, driver_holder.the_driver.current_url, None)
                    driver_holder.click_element(e, link_info)
                    href = driver_holder.the_driver.current_url
                    driver_holder.the_driver.back()
                urls.add(href)
        except Exception as exp:
            logger.error(exp)
    return urls


def start_selenium_for_tests(logger, args, scroll_to_bottom_and_wait_more_results=True):
    if os.path.exists("geckodriver.log"):
        os.unlink("geckodriver.log")

    if args.download_folder is not None:
        if os.path.exists(args.download_folder):
            shutil.rmtree(args.download_folder, ignore_errors=True)
        os.mkdir(args.download_folder)
    try:
        driver_holder = TSeleniumDriver(logger, headless=args.headless,
                                        download_folder=args.download_folder,
                                        loglevel="trace",
                                        scroll_to_bottom_and_wait_more_results=scroll_to_bottom_and_wait_more_results)
        driver_holder.start_executable()
    except Exception as exp:
        logger.error(exp)
        sys.exit(1)
    return driver_holder


def error_exit(driver_holder, message):
    print(message)
    driver_holder.stop_executable()
    sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging("check_selenium.log")
    driver_holder = start_selenium_for_tests(logger, args)
    logger.info("navigate to {}\n".format(args.source_url))
    links = driver_holder.navigate_and_get_links(args.source_url)
    logger.info("Title:{}, type={}\n".format(driver_holder.the_driver.title, type(driver_holder.the_driver.title)))
    logger.info("html len: {0}".format(len(driver_holder.the_driver.page_source)))
    links_count = len(links)
    logger.info("links and buttons found: {0}".format(links_count))
    if args.anchor is not None:
        found_urls = get_links(logger, links, args.anchor)
        if len(found_urls) == 0:
            error_exit(driver_holder, "no links with the given anchor found")

        if args.assert_child_url is not None:
            if args.assert_child_url not in found_urls:
                error_exit(driver_holder, "cannot find {} in sublinks".format(args.assert_child_url))

    if args.check_scroll_down:
        driver_holder.scroll_to_bottom_and_wait_more_results = False
        logger.info("navigate to {}\n".format(args.source_url))
        links1 = driver_holder.navigate_and_get_links(args.source_url)
        links_count_without_scroll_down = len(links1)
        if links_count <= links_count_without_scroll_down:
            error_exit(driver_holder,"no additional information with page scroll down found")

    driver_holder.stop_executable()