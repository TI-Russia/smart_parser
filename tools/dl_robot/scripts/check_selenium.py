from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging
from common.link_info import TLinkInfo, TClickEngine

import argparse
import os
import json
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--firefox", dest='use_firefox', required=False, action="store_true", default=False)
    parser.add_argument("--gui", dest='gui', required=False, action="store_true", default=False)
    parser.add_argument("--action", dest='action', required=False, default="title",
                        help="can be title, links, click, speed, head default action is title")
    parser.add_argument("--element-index", dest='element_index', required=False, type=int, default=0)
    parser.add_argument("--element-id", dest='element_id', required=False)
    parser.add_argument("--download-folder", dest='download_folder', required=False, default=None)
    parser.add_argument("--repeat-count", dest='repeat_count', type=int, default=1)
    parser.add_argument("urls", nargs="*")
    args = parser.parse_args()
    return args


def get_square_area(element):
    return element.rect.get('height', 0) * element.rect.get('width', 0)


def print_links (driver_holder, url):
    elements = driver_holder.navigate_and_get_links(url)
    print("elements count: {}".format(len(elements)))
    for element_index in range(len(elements)):
        element = elements[element_index]
        rec = {'index': element_index,
               'href': element.get_attribute('href'),
               'anchor': element.text,
               'area': get_square_area(element)}
        print(json.dumps(rec, ensure_ascii=False))


def click(driver_holder, url, element_index):
    elements = driver_holder.navigate_and_get_links(url)
    element = elements[element_index]
    print ("click element {} anchor={}".format(element_index, element.text))
    link_info = TLinkInfo(TClickEngine.selenium, url, None, anchor_text=element.text)
    driver_holder.click_element(element, link_info)
    print("href={}".format(link_info.target_url))
    print("downloaded_file={}".format(link_info.downloaded_file))


def calc_page_speed(driver_holder, url, element_id):
    start = time.time()
    driver_holder.the_driver.get(url)
    WebDriverWait(driver_holder.the_driver, 5).until(EC.presence_of_element_located((By.ID, element_id)))
    end = time.time()
    return int((end - start) * 1000)


def httphead(driver_holder, url):
    from seleniumrequests import Chrome
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    options = ChromeOptions()
    options.headless = True
    webdriver = Chrome(options=options)
    response = webdriver.request('HEAD', url)
    print(response.headers)
    webdriver.close()


def pagespeed(driver_holder, url, element_id, repeat_count):
    times = list()
    times.append(calc_page_speed(driver_holder, url, element_id))

    for i in range(repeat_count - 1):
        driver_holder.the_driver.get("http://google.com")
        times.append(calc_page_speed(driver_holder, url, element_id))

    print("repeat_count = {}, elapsed time sum (ms): {}, average={}".format(repeat_count, sum(times),
          sum(times) / (repeat_count + 0.00000000000000001)))


if __name__ == '__main__':
    logger = setup_logging(log_file_name="check_selenium.log")
    args = parse_args()
    if os.path.exists("geckodriver.log"):
        logger.info("rm geckodriver.log")
        os.unlink("geckodriver.log")
    use_chrome = True
    if args.use_firefox:
        use_chrome = False
    if args.download_folder is not None:
        if not os.path.exists(args.download_folder):
            os.makedirs(args.download_folder)
        args.download_folder = os.path.abspath(args.download_folder)
    driver = TSeleniumDriver(logger, headless=(not args.gui), download_folder=args.download_folder,
                             loglevel="DEBUG", start_retry_count=1, use_chrome=use_chrome)
    driver.start_executable()
    if len(args.urls) > 0:
        url = args.urls[0]
        if not url.startswith("http"):
            url = "http://" + url
    else:
        url = "http://www.aot.ru"
    print("navigate {}".format(url))
    if args.action == "title":
        driver.navigate(url)
        print("Title: {}".format(driver.the_driver.title))
    elif args.action == "links":
        print_links(driver, url)
    elif args.action.startswith("click"):
        click(driver, url, args.element_index)
    elif args.action.startswith("speed"):
        pagespeed(driver, url, args.element_id, args.repeat_count)
    elif args.action.startswith("head"):
        httphead(driver, url)
    else:
        print("unknown action {}".format(args.action))

    driver.stop_executable()