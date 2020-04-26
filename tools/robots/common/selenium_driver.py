from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from robots.common.content_types import ALL_CONTENT_TYPES
import logging
from selenium.common.exceptions  import WebDriverException, NoSuchWindowException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import os
import shutil
from pathlib import Path
import time
from contextlib import contextmanager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of

def make_folder_empty(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


class TSeleniumDriver:
    def __init__(self, headless=True, download_folder=None):
        self.the_driver = None
        self.driver_processed_urls_count  = 0
        self.download_folder = download_folder
        assert download_folder != "."
        self.headless = headless
        self.last_downloaded_file = None
        self.window_before_click = None

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

    def _navigate_and_get_links(self, url, timeout=6):
        self.navigate(url)
        time.sleep(timeout)
        links = self.get_buttons_and_links()
        try:
            for link in links:
                text = link.text
                return links
        finally:
            #  second timeout
            time.sleep(timeout)
            return self.get_buttons_and_links()

    def navigate_and_get_links(self, url, timeout=6):
        try:
            return self._navigate_and_get_links(url, timeout)
        except (WebDriverException, NoSuchWindowException) as exp:
            logger = logging.getLogger("dlrobot_logger")
            logger.error(
                "exception during selenium navigate and get elements, exception={}, try restart".format(str(exp)))
            self.stop_executable()
            self.start_executable()
            time.sleep(10)
            return self._navigate_and_get_links(url, timeout)

    def wait_download_finished(self, timeout=120):
        dl_wait = True
        seconds = 0
        while dl_wait and seconds < timeout:
            firefox_temp_file = sorted(Path(self.download_folder).glob('*.part'))
            chrome_temp_file = sorted(Path(self.download_folder).glob('*.crdownload'))
            if (len(firefox_temp_file) == 0) and \
                    (len(chrome_temp_file) == 0):
                files = os.listdir(self.download_folder)
                if len(files) > 0:
                    return save_download_file(os.path.join(self.download_folder, files[0]))
                return None
            time.sleep(1)
            seconds += 1
        return None

    def click_element(self, element):
        self.last_downloaded_file = None
        if self.download_folder is not None:
            make_folder_empty(self.download_folder)
        self.window_before_click = self.the_driver.window_handles[0]
        self.the_driver.execute_script("arguments[0].scrollIntoView({block: \"center\", behavior: \"smooth\"});", element)
        time.sleep(1)
        # open in a new tab, send ctrl-click
        ActionChains(self.the_driver) \
            .key_down(Keys.CONTROL) \
            .click(element) \
            .key_up(Keys.CONTROL) \
            .perform()

        time.sleep(6)
        if len(self.the_driver.window_handles) < 2:
            logger = logging.getLogger("dlrobot_logger")
            logger.debug("cannot click, no new window is found")
            return
        window_after = self.the_driver.window_handles[1]
        self.the_driver.switch_to_window(window_after)
        if self.download_folder is not None:
            self.last_downloaded_file = self.wait_download_finished(180)

    def close_window_tab(self):
        self.the_driver.close()
        assert self.window_before_click  is not None
        self.the_driver.switch_to.window(self.window_before_click)
