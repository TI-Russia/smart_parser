from common.link_info import TLinkInfo, TClickEngine
from web_site_db.robot_web_site import TRobotStep
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from selenium.webdriver.support.ui import Select
import time


def tomsk_gov_ru(web_site: TWebSiteCrawlSnapshot, max_download_count=20):
    web_site.create_export_folder()
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    driver.navigate("https://tomsk.gov.ru/antiCorruption/front/public")
    download_count = 0
    year_element = driver.the_driver.find_element_by_name("year")
    year_select = Select(year_element)
    for i in range(len(list(year_select.options))):
        year_select.select_by_index(i)
        robot_step.logger.info("select year {}".format(year_element.get_attribute("value")))
        time.sleep(3)
        for c in driver.the_driver.find_elements_by_class_name("toggle"):
            robot_step.logger.info("click toggle element")
            c.click()
            time.sleep(2)
        element_index = 0
        for c1 in driver.the_driver.find_elements_by_partial_link_text("Скачать"):
            element_index += 1
            robot_step.logger.info("click {}".format(c1.get_attribute("href")))
            c1.click()
            time.sleep(1)
            downloaded_file = driver.wait_download_finished()
            if downloaded_file is not None:
                href = c1.get_attribute("href")
                if href is None:
                    href = robot_step.website.morda_url
                link_info = TLinkInfo(TClickEngine.selenium,
                          href,
                          None,
                          source_html="", anchor_text="", tag_name="a",
                          element_index=element_index,
                          source_page_title="", downloaded_file=downloaded_file)
                robot_step.add_downloaded_file_wrapper(link_info)

            download_count += 1
            if max_download_count is not None and download_count >= max_download_count:
                time.sleep(2)
                return
