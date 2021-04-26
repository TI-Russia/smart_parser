from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging
import sys


if __name__ == '__main__':
    logger = setup_logging(log_file_name="check_selenium.log")
    driver = TSeleniumDriver(logger, True)
    driver.start_executable()
    if len(sys.argv) > 1:
        url = sys.argv[1]
        if not url.startswith("http"):
            url = "http://" + url
    else:
        url = "http://www.aot.ru"
    print("navigate {}".format(url))
    driver.navigate(url)
    print("Title: {}".format(driver.the_driver.title))
