from common.download import save_downloaded_file
from common.link_info import TLinkInfo
from common.content_types import ALL_CONTENT_TYPES
from common.http_request import THttpRequester

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
from selenium.webdriver.common.action_chains import ActionChains

import os
import shutil
from pathlib import Path
import time


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

    def __init__(self, logger, headless=True, download_folder=None, loglevel=None,
                 scroll_to_bottom_and_wait_more_results=True, start_retry_count=3):
        self.logger = logger
        self.the_driver = None
        self.driver_processed_urls_count = 0
        self.download_folder = download_folder
        assert download_folder != "."
        self.headless = headless
        self.loglevel = loglevel
        self.start_retry_count = start_retry_count
        self.scroll_to_bottom_and_wait_more_results = scroll_to_bottom_and_wait_more_results

    def start_executable(self):
        options = FirefoxOptions()
        options.headless = self.headless
        options.log.level = self.loglevel
        # see http://kb.mozillazine.org/About:config_Entries for all preferences
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.manager.closeWhenDone", True)
        options.set_preference("browser.download.manager.focusWhenStarting", False)
        if self.download_folder is not None:
            assert os.path.isdir(self.download_folder)
            options.set_preference("browser.download.dir", self.download_folder)
            options.set_preference("browser.download.manager.showAlertOnComplete", False)
            options.set_preference("browser.helperApps.neverAsk.saveToDisk", ALL_CONTENT_TYPES)
            options.set_preference("browser.helperApps.alwaysAsk.force", False)
            options.set_preference("pdfjs.disabled", True)
            options.set_preference("plugin.scan.Acrobat", "99.0")
            options.set_preference("plugin.scan.plid.all", False)
        for retry in range(self.start_retry_count):
            try:
                self.the_driver = webdriver.Firefox(options=options)
                #self.the_driver.implicitly_wait(10)
                break
            except (WebDriverException, InvalidSwitchToTargetException) as exp:
                if retry == self.start_retry_count - 1:
                    raise
                self.logger.error("Cannot start selenium, exception:{}, sleep and retry...".format(str(exp)))
                time.sleep(10)

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

        #leave only one window tab, close other tabs
        while len(self.the_driver.window_handles) > 1:
            self.the_driver.switch_to.window(self.the_driver.window_handles[len(self.the_driver.window_handles) - 1])
            self.the_driver.close()
        self.logger.debug("selenium navigate to {}, window tabs count={}".format(url, len(self.the_driver.window_handles)))
        self.the_driver.switch_to.window(self.the_driver.window_handles[0])

        # navigation
        try:
            self.the_driver.get(url)
        except IndexError as exp:
            raise THttpRequester.RobotHttpException("general IndexError inside urllib.request.urlopen",
                                                    url, 520, "GET")

    def get_buttons_and_links(self):
        return list(self.the_driver.find_elements_by_xpath('//button | //a'))

    def _navigate_and_get_links(self, url, timeout=4):
        self.logger.debug("navigate to {}".format(url))
        self.navigate(url)

        self.logger.debug("sleep for {}".format(timeout))
        time.sleep(timeout)

        body = self.the_driver.find_element_by_tag_name('body')

        self.logger.debug("scroll down")
        if self.scroll_to_bottom_and_wait_more_results and body:
            self.the_driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            self.the_driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        try:
            return self.get_buttons_and_links()
        except Exception as exp:
            self.logger.error("Exception = {}, retry get links, after timeout".format(exp))
            #  second timeout
            time.sleep(timeout)
            return self.get_buttons_and_links()

    def restart(self):
        self.logger.error("restart selenium")
        self.stop_executable()
        self.start_executable()
        time.sleep(10)

    def navigate_and_get_links(self, url, timeout=6):
        try:
            return self._navigate_and_get_links(url, timeout)
        except (WebDriverException, InvalidSwitchToTargetException) as exp:
            self.logger.error("exception during selenium navigate and get elements: {}".format(str(exp)))
            self.restart()
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
                    return save_downloaded_file(os.path.join(self.download_folder, files[0]))
                return None
            time.sleep(1)
            seconds += 1
        return None

    def click_element(self, element, link_info: TLinkInfo):
        if self.download_folder is not None:
            make_folder_empty(self.download_folder)
        assert link_info.target_url is None
        save_current_url = self.the_driver.current_url  # may differ from link_info.SourceUrl, because of redirects

        ActionChains(self.the_driver).move_to_element(element)

        element.click()
        time.sleep(6)
        if self.download_folder is not None:
            link_info.downloaded_file = self.wait_download_finished(180)

        if link_info.downloaded_file is None:
            if self.the_driver.current_url != link_info.source_url:
                link_info.target_url = self.the_driver.current_url
                link_info.target_title = self.the_driver.title
        if self.the_driver.current_url != save_current_url:
            self.the_driver.back()
        if self.the_driver.current_url != save_current_url:
            self.the_driver.get(link_info.source_url)  # hope it leads to save_current_url
            if save_current_url != link_info.source_url:
                self.logger.debug("cannot switch to the saved url must be {}, got {}, keep going".format(
                    save_current_url, self.the_driver.current_url))


