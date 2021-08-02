from common.download import save_downloaded_file
from common.link_info import TLinkInfo
from common.content_types import ALL_CONTENT_TYPES, is_video_or_audio_file_extension
from common.http_request import THttpRequester

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions

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
                 scroll_to_bottom_and_wait_more_results=True, start_retry_count=3, use_chrome=True, verbose=False):
        self.logger = logger
        self.the_driver: webdriver.WebDriver = None
        self.driver_processed_urls_count = 0
        self.download_folder = download_folder
        assert download_folder != "."
        self.headless = headless
        #self.headless = False
        self.loglevel = loglevel
        self.verbose = verbose
        self.use_chrome = use_chrome
        self.start_retry_count = start_retry_count
        self.scroll_to_bottom_and_wait_more_results = scroll_to_bottom_and_wait_more_results

    def start_executable(self):
        if self.use_chrome:
            self.start_executable_chrome()
        else:
            self.start_executable_firefox()

    def start_executable_firefox(self):
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

    def start_executable_chrome(self):
        options = ChromeOptions()
        options.headless = self.headless
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        options.add_argument("user-agent={}".format(user_agent))

        prefs = {
            'download.default_directory': self.download_folder,

             # it does not work, use environment variable LANG as it stated at https://bugs.chromium.org/p/chromium/issues/detail?id=755338
             #'intl.accept_languages': 'ru,ru_RU'  # to do: it for Firefox
             #'intl.accept_languages': 'ru'  # to do: it for Firefox

        }
        options.add_experimental_option('prefs', prefs)
        save_LANG = os.environ.get('LANG')
        service_args = ["--log-path=geckodriver.log"]
        if self.verbose:
            service_args.append("--verbose")
        for retry in range(self.start_retry_count):
            try:
                os.environ['LANG'] = 'ru'
                self.the_driver = webdriver.Chrome(options=options, service_args=service_args)
                self.the_driver.set_window_size(1440, 900)
                break
            except (WebDriverException, InvalidSwitchToTargetException) as exp:
                if retry == self.start_retry_count - 1:
                    raise
                self.logger.error("Cannot start selenium, exception:{}, sleep and retry...".format(str(exp)))
                time.sleep(10)
            finally:
                os.environ['LANG'] = save_LANG

    def stop_executable(self):
        if self.the_driver is not None:
            self.the_driver.quit()

    def close_not_first_tab(self):
        while len(self.the_driver.window_handles) > 1:
            self.the_driver.switch_to.window(self.the_driver.window_handles[len(self.the_driver.window_handles) - 1])
            self.the_driver.close()

    def navigate(self, url):
        #to reduce memory usage
        if self.driver_processed_urls_count > 100:
            self.stop_executable()
            self.start_executable()
            self.driver_processed_urls_count = 0
        self.driver_processed_urls_count += 1

        #leave only one window tab, close other tabs
        self.close_not_first_tab()
        self.logger.debug("selenium navigate to {}, window tabs count={}".format(url, len(self.the_driver.window_handles)))
        self.the_driver.switch_to.window(self.the_driver.window_handles[0])

        # navigation
        try:
            self.the_driver.set_page_load_timeout(20)
            self.the_driver.get(url)
        except IndexError as exp:
            raise THttpRequester.RobotHttpException("general IndexError inside urllib.request.urlopen",
                                                    url, 520, "GET")
        except TimeoutException as exp:
            title = self.the_driver.title
            if len(title) == 0:
                raise
        finally:
            self.the_driver.set_page_load_timeout(30)

    def get_buttons_and_links(self):
        return list(self.the_driver.find_elements_by_xpath('//button | //a'))

    def get_links_js(self, timeout=4):
        js = """
                function add_link(el, element_list) {
                    el.scrollIntoView();
                    element_list.push({"id":el, "href": el.href, "anchor": el.innerText, "class":el.className})
                }
                hrefs = [];
                buttons = document.getElementsByTagName("button");
                [].forEach.call(buttons, function (el) { add_link(el, hrefs);  });

                links = document.getElementsByTagName("a");
                [].forEach.call(links, function (el) { add_link(el, hrefs);  });
                return hrefs;
            """

        try:
            return self.the_driver.execute_script(js)
        except Exception as exp:
            self.logger.error("Exception = {}, retry get links, after timeout".format(exp))
            #  second timeout
            time.sleep(timeout)
            return self.the_driver.execute_script(js)

    def _navigate_and_get_links_js(self, url, timeout=4):
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
        return self.get_links_js()


    def restart(self):
        self.logger.error("restart selenium")
        self.stop_executable()
        self.start_executable()
        time.sleep(10)

    def navigate_and_get_links_js(self, url, timeout=4):
        try:
            return self._navigate_and_get_links_js(url, timeout)
        except (WebDriverException, InvalidSwitchToTargetException) as exp:
            self.logger.error("exception during selenium navigate and get elements: {}".format(str(exp)))
            self.restart()
            return self._navigate_and_get_links_js(url, timeout)

    def wait_download_finished(self, timeout=120):
        dl_wait = True
        seconds = 0
        while dl_wait and seconds < timeout:
            browser_temp_file = sorted(Path(self.download_folder).glob('*.part'))
            chrome_temp_file = sorted(Path(self.download_folder).glob('*.crdownload'))
            if (len(browser_temp_file) == 0) and \
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

        ActionChains(self.the_driver)\
            .move_to_element(element)\
            .pause(1)\
            .key_down(Keys.CONTROL) \
            .click(element)\
            .key_up(Keys.CONTROL) \
            .perform()

        #print (element.)
        time.sleep(3)

        #element.click()
        #time.sleep(6)
        if self.download_folder is not None:
            link_info.downloaded_file = self.wait_download_finished(180)

        if len(self.the_driver.window_handles) > 1:
            try:
                self.the_driver.switch_to.window(
                    self.the_driver.window_handles[len(self.the_driver.window_handles) - 1])
                if self.the_driver.current_url != link_info.source_url and self.the_driver.current_url != 'about:blank':
                    link_info.set_target(self.the_driver.current_url, self.the_driver.title)
            except WebDriverException as exp:
                pass
            except Exception as exp:
                pass
            self.close_not_first_tab()
            self.the_driver.switch_to.window(self.the_driver.window_handles[0])
            if self.the_driver.current_url != save_current_url:
                self.logger.error("cannot switch to the saved url must be {}, got {}, keep going".format(
                    save_current_url, self.the_driver.current_url))


