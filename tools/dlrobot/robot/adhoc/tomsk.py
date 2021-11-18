from dlrobot.common.robot_web_site import TWebSiteCrawlSnapshot
from selenium.webdriver.support.ui import Select
import time


def tomsk_gov_ru(web_site: TWebSiteCrawlSnapshot):
    web_site.create_export_folder()
    robot_step = web_site.robot_steps[-1]
    driver = robot_step.get_selenium_driver()
    driver.navigate("https://tomsk.gov.ru/antiCorruption/front/public")
    year_element = driver.the_driver.find_element_by_name("year")
    year_select = Select(year_element)
    for i in range(len(list(year_select.options))):
        year_select.select_by_index(i)
        declaration_year = year_element.get_attribute("value")
        if declaration_year is None or not declaration_year.isdigit():
            robot_step.logger.info("skip not year select item: {}".format(declaration_year))
            continue
        else:
            declaration_year = int(declaration_year)
        robot_step.logger.info("select year {}".format(declaration_year))
        time.sleep(3)
        for c in driver.find_elements_by_class_name("toggle"):
            robot_step.logger.info("click toggle element")
            c.click()
            time.sleep(2)
        for c1 in driver.find_elements_by_partial_link_text("Скачать"):
            href = c1.get_attribute("href")
            robot_step.logger.info("click {}".format(href))
            c1.click()
            time.sleep(1)
            downloaded_file = driver.wait_download_finished()
            if downloaded_file is not None:
                robot_step.add_downloaded_file_manually(downloaded_file, href, declaration_year=declaration_year)
