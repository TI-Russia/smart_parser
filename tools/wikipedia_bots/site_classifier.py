from common.selenium_driver import TSeleniumDriver
from common.logging_wrapper import setup_logging
import sys


if __name__ == '__main__':
    logger = setup_logging(log_file_name="classifier.log")
    driver = TSeleniumDriver(logger, False)
    driver.start_executable()
    with open ("web_sites_to_deprecate.txt.result", "w") as outp:
        with open("web_sites_to_deprecate.txt", "r") as inp:
            for url in inp:
                url = url.strip()
                driver.navigate("http://" + url)
                logger.info(url)
                answer = sys.stdin.readline().strip()
                outp.write("{} {}\n ".format(url.strip(), answer))
                outp.flush()