from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging
from selenium.webdriver.support.ui import Select
from web_site_db.robot_project import TRobotProject

import argparse
import os
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-url", dest='input_url', required=False)
    parser.add_argument("--gui", dest='gui', required=False, action="store_true", default=False)
    parser.add_argument("--download-folder", dest='download_folder', required=False, default=None)
    parser.add_argument("--max-download-count", dest='max_download_count', type=int, default=None)
    return parser.parse_args()


def tomsk_gov_ru(logger, selenium_driver, max_download_count):
    selenium_driver.navigate("https://tomsk.gov.ru/antiCorruption/front/public")
    download_count = 0
    year_element = selenium_driver.the_driver.find_element_by_name("year")
    year_select = Select(year_element)
    for i in range(len(list(year_select.options))):
        year_select.select_by_index(i)
        logger.info("select year {}".format(year_element.get_attribute("value")))
        time.sleep(3)
        for c in selenium_driver.the_driver.find_elements_by_class_name("toggle"):
            logger.info("click toggle element")
            c.click()
            time.sleep(2)
        for c1 in selenium_driver.the_driver.find_elements_by_partial_link_text("Скачать"):
            logger.info("click {}".format(c1.get_attribute("href")))
            c1.click()
            time.sleep(2)
            download_count += 1
            if max_download_count is not None and download_count >= max_download_count:
                time.sleep(2)
                return


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(log_file_name="selenium_clicker.log")

    if args.download_folder is not None:
        if not os.path.exists(args.download_folder):
            os.makedirs(args.download_folder)
        args.download_folder = os.path.abspath(args.download_folder)

    driver = TSeleniumDriver(logger, headless=(not args.gui), download_folder=args.download_folder,
                             loglevel="DEBUG", start_retry_count=1)
    driver.start_executable()
    tomsk_gov_ru(logger, driver, max_download_count=args.max_download_count)
    driver.stop_executable()

    robot_project_path = TRobotProject.create_project_from_exported_files(
        logger,
        "tomsk.gov.ru",
        list(os.path.join(args.download_folder, f) for f in os.listdir(args.download_folder))
    )

