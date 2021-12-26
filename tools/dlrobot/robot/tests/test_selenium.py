from common.selenium_driver import TSeleniumDriver
from common.link_info import TLinkInfo, TClickEngine
from common.download import TDownloadEnv
from common.logging_wrapper import close_logger, setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv

import os
import shutil
from unittest import TestCase


class TestSelenium(TestCase):

    def filter_link_elements_by_anchor(self, link_elements, start_anchor_text):
        urls_and_elements = set()
        for element_index, element in enumerate(link_elements):
            try:
                if element['anchor'] is None:
                    continue
                link_text = element['anchor'].strip('\n\r\t ')
                self.logger.debug("check link anchor={}, element_index={}".format(link_text, element_index))
                if link_text.lower().startswith(start_anchor_text.lower()):
                    self.logger.debug("found link anchor={}".format(link_text))
                    href = element['href']
                    if href is None:
                        link_info = TLinkInfo(TClickEngine.selenium, driver_holder.the_driver.current_url, None)
                        self.driver_holder.click_element(element['id'], link_info)
                        href = self.driver_holder.the_driver.current_url
                        self.driver_holder.the_driver.back()
                    urls_and_elements.add((href, element['id']))
            except Exception as exp:
                self.logger.error(exp)
        return urls_and_elements

    def setUp(self):
        self.env = TestDlrobotEnv("data.selenuim")

        self.logger = setup_logging(log_file_name="check_selenium.log")
        self.download_folder = os.path.join(self.env.data_folder, "download")
        os.mkdir(self.download_folder)
        try:
            self.driver_holder = TSeleniumDriver(self.logger, headless=True,
                                            download_folder=self.download_folder,
                                            loglevel="trace",
                                            scroll_to_bottom_and_wait_more_results=True)
            self.driver_holder.start_executable()
        except Exception as exp:
            self.logger.error(exp)
            raise

    def tearDown(self):
        self.driver_holder.stop_executable()
        close_logger(self.logger)
        self.env.delete_temp_folder()

    def get_all_link_elements(self, url):
        self.logger.info("navigate to {}\n".format(url))
        links = self.driver_holder.navigate_and_get_links_js(url)
        #self.logger.info("Title:{}, type={}\n".format(self.driver_holder.the_driver.title,
        #                                              type(self.driver_holder.the_driver.title)))
        #self.logger.info("html len: {0}".format(len(self.driver_holder.the_driver.page_source)))
        return links

    def check_anchor(self, elements, anchor, child_url=None):
        urls_and_elements = self.filter_link_elements_by_anchor(elements, anchor)
        self.assertGreater(len(urls_and_elements), 0,  msg="no links with the given anchor found")

        if child_url is not None:
            found_urls = list(url for (url, elem) in urls_and_elements)
            self.assertIn(child_url, found_urls, msg="cannot find {} in sublinks".format(child_url))
        return urls_and_elements

    def check_scroll_down(self, url, links_with_scroll_down):
        self.driver_holder.scroll_to_bottom_and_wait_more_results = False
        #self.logger.info("navigate to {}\n".format(url))
        links_without_scroll_down = self.driver_holder.navigate_and_get_links_js(url)
        self.assertGreater(len(links_with_scroll_down), len(links_without_scroll_down),
                           msg="no additional information with page scroll down found")

    def test_selenium_mid(self):
        elements = self.get_all_link_elements('http://www.mid.ru')
        self.check_anchor(elements, "противодействие")

    def test_download_pdf(self):
        shutil.rmtree(TDownloadEnv.get_download_folder(), ignore_errors=True)
        elements = self.get_all_link_elements('http://aot.ru/docs/Nozhov')
        url_and_elements = self.check_anchor(elements, "supplement1")
        url, element = list(url_and_elements)[0]
        link_info = TLinkInfo(TClickEngine.selenium, url, None)
        self.driver_holder.click_element(element, link_info)
        self.driver_holder.wait_download_finished()
        download_files = os.listdir(TDownloadEnv.get_download_folder())
        self.assertTrue(len(download_files), 1)

    def test_download_doc(self):
        shutil.rmtree(TDownloadEnv.get_download_folder(), ignore_errors=True)
        elements = self.get_all_link_elements('http://aot.ru/doc_examples/test.html')
        url_and_elements = self.check_anchor(elements, "test.doc")
        url, element = list(url_and_elements)[0]
        link_info = TLinkInfo(TClickEngine.selenium, url, None)
        self.driver_holder.click_element(element, link_info)
        self.driver_holder.wait_download_finished()
        download_files = os.listdir(TDownloadEnv.get_download_folder())
        self.assertTrue(len(download_files), 1)

    def test_scroll_down(self):
        url = 'https://minpromtorg.gov.ru/search_results/?date_from_38=&date_to_38=&q_38=%D0%B8%D0%BC%D1%83%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%BE&sortby_38=date&sources_38%5B%5D=contents_news%2Ccontents_documents_list%2Ccontents_documents_list_file%2Ccontents_files_list%2Ccontents_npa%2Ccontents_person%2Ccontents_dep%2Ccontents_regions%2Ccontents_text%2Ccontents_list&source_id_38=1&spec_filter_38%5B%5D='
        link_elements = self.get_all_link_elements(url)
        self.check_scroll_down(url,link_elements)

    def test_ugorsk(self):
        elements = self.get_all_link_elements('http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278')
        self.check_anchor(elements, "загрузить")

    # todo: I do not  know how to make selenium work for https://minvr.ru/press-center/collegium/5167/?doc=1
    # since http header are application/octet-stream, but it is a real html, so firefox won't open it, just timeouted for 5 minutes
    #def test_minvr(self):
    #    shutil.rmtree(TDownloadEnv.get_download_folder(), ignore_errors=True)
    #    url = 'https://minvr.ru/press-center/collegium/5167/?doc=1'
    #    self.driver_holder.navigate(url)

