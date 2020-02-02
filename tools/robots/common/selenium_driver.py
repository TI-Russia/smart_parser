from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from content_types import  ALL_CONTENT_TYPES
import time
from selenium.common.exceptions  import WebDriverException, NoSuchWindowException

class TSeleniumDriver:
    def __init__(self, headless=True):
        self.the_driver = None
        self.driver_processed_urls_count  = 0
        self.download_folder = None
        self.headless = headless

    def start_executable(self):
        options = FirefoxOptions()
        options.headless = self.headless
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.manager.closeWhenDone", True)
        options.set_preference("browser.download.manager.focusWhenStarting", False)
        if self.download_folder is not None:
            options.set_preference("browser.download.dir", self.download_folder)
            options.set_preference("browser.helperApps.neverAsk.saveToDisk", ALL_CONTENT_TYPES)
            options.set_preference("browser.helperApps.alwaysAsk.force", False)
        self.the_driver = webdriver.Firefox(firefox_options=options)

    def stop_executable(self):
        if self.the_driver is not None:
            self.the_driver.quit()

    def navigate(self, url):
        #to reduce memory usage
        if self.driver_processed_urls_count > 100:
            self.stop_executable()
            self.start_executable()
            self.driver_processed_urls_count = 0
        self.driver_processed_urls_count += 1
        while len(self.the_driver.window_handles) > 1:
            self.the_driver.close()
        self.the_driver.get(url)

    def get_buttons_and_links(self):
        return list(self.the_driver.find_elements_by_xpath('//button | //a'))

    def _navigate_and_get_links(self, url):
        self.navigate(url)
        time.sleep(6)
        return self.get_buttons_and_links()

    def navigate_and_get_links(self, url):
        try:
            return self._navigate_and_get_links(url)
        except (WebDriverException, NoSuchWindowException) as exp:
            logger = logging.getLogger("dlrobot_logger")
            logger.error(
                "exception during selenium navigate and get elements, exception={}, try restart".format(str(exp)))
            self.stop_executable()
            self.start_executable()
            time.sleep(6)
            return self._navigate_and_get_links(url)


