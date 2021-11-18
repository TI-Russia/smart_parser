from dlrobot.common.robot_web_site import TWebSiteCrawlSnapshot
from common.link_info import TLinkInfo, TClickEngine
from common.selenium_driver import TSeleniumDriver

from selenium.common.exceptions  import WebDriverException
import time


def download_from_tgl_serp(web_site: TWebSiteCrawlSnapshot, sved_url):
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    hrefs = list()
    for c in driver.find_elements_by_class_name("dl"):
        try:
            href = c.get_attribute("href")
            if href is not None:
                hrefs.append(href)
        except WebDriverException as exp:
            robot_step.logger.error("skip {}, exception {}".format(c))

    for href in hrefs:
        robot_step.logger.info("download {}".format(href))
        link_info = TLinkInfo(TClickEngine.manual, sved_url, href)
        robot_step.add_link_wrapper(link_info)


def click_next_page(web_site: TWebSiteCrawlSnapshot):
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    page_button_arr = driver.find_elements_by_class_name("next")
    if len(page_button_arr) == 0:
        return False
    page_button_arr[0].click()
    time.sleep(3)
    return True


def tgl_ru(web_site: TWebSiteCrawlSnapshot):
    web_site.create_export_folder()
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    sved_url = "https://tgl.ru/municipal-service/svedeniya-o-dohodah/"
    driver.navigate(sved_url)
    robot_step.add_link_wrapper(TLinkInfo(TClickEngine.manual, robot_step.website.main_page_url, sved_url))
    page_no = 1

    while True:
        download_from_tgl_serp(web_site, sved_url)
        if not click_next_page(web_site):
            break
        page_no += 1
    robot_step.logger.info("processed {} pages".format(page_no))
