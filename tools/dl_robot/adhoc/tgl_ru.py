from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from common.link_info import TLinkInfo, TClickEngine

import time


def tgl_ru(web_site: TWebSiteCrawlSnapshot):
    web_site.create_export_folder()
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    sved_url = "https://tgl.ru/municipal-service/svedeniya-o-dohodah/"
    driver.navigate(sved_url)
    robot_step.add_link_wrapper(TLinkInfo(TClickEngine.manual, robot_step.website.main_page_url, sved_url))
    page_no = 1
    while True:
        for c in driver.the_driver.find_elements_by_class_name("dl"):
             href = c.get_attribute("href")
             robot_step.logger.info("download {}".format(href))
             link_info = TLinkInfo(TClickEngine.manual, sved_url, href)
             robot_step.add_link_wrapper(link_info)

        page_no += 1
        next_page = driver.the_driver.find_element_by_partial_link_text("{}".format(page_no))
        if next_page is None:
            break
        robot_step.logger.info("click page {}".format(page_no))
        next_page.click()
        time.sleep(3)
