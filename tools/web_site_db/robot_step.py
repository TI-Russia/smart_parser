from common.download import TDownloadedFile, DEFAULT_HTML_EXTENSION, are_web_mirrors
from common.primitives import prepare_for_logging, strip_viewer_prefix, get_site_domain_wo_www
from common.html_parser import THtmlParser
from common.link_info import TLinkInfo, TClickEngine
from common.primitives import get_html_title
from common.http_request import THttpRequester
from common.popular_sites import is_super_popular_domain

from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
import time
from collections import defaultdict
import urllib
import re
import signal


class OnePageProcessingTimeoutException(Exception):
    pass


class TUrlMirror:
    def __init__(self, url):
        self.input_url  = url
        self.protocol_prefix = ''
        self.www_prefix = ''
        for prefix in ['http://', 'https://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                self.protocol_prefix = prefix
                break
        for prefix in ['www']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                self.www_prefix = prefix
        self.normalized_url = url


class TUrlInfo:
    def __init__(self, title=None, step_name=None, init_json=None):
        if init_json is not None:
            self.step_name = init_json['step']
            self.title = init_json['title']
            self.parent_nodes = set(init_json.get('parents', list()))
            self.linked_nodes = init_json.get('links', dict())
            self.downloaded_files = list()
            for rec in init_json.get('downloaded_files', list()):
                self.downloaded_files.append(TLinkInfo(None, None, None).from_json(rec))
        else:
            self.step_name = step_name
            self.title = title
            self.parent_nodes = set()
            self.linked_nodes = dict()
            self.downloaded_files = list()

    def to_json(self):
        record = {
            'step': self.step_name,
            'title': self.title,
            'parents': list(self.parent_nodes),
            'links': self.linked_nodes,
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = list(x.to_json() for x in self.downloaded_files)
        return record

    def add_downloaded_file(self, link_info: TLinkInfo):
        self.downloaded_files.append(link_info)

    def add_child_link(self, href, record):
        self.linked_nodes[href] = record

# see https://sutr.ru/about_the_university/svedeniya-ob-ou/education/ with 20000 links
MAX_LINKS_ON_ONE_WEB_PAGE = 1000


def get_office_domain(web_domain):
    index = 2
    if web_domain.endswith("gov.ru"):
        index = 3 #minpromtorg.gov.ru

    return ".".join(web_domain.split(".")[-index:])


def check_href_elementary(href):
    if href.startswith('mailto:'):
        return False
    if href.startswith('tel:'):
        return False
    if href.startswith('javascript:'):
        return False
    if href.startswith('about:'):
        return False
    if href.startswith('consultantplus:'):
        return False
    if href.startswith('#'):
        if not href.startswith('#!'): # it is a hashbang (a starter for AJAX url) http://minpromtorg.gov.ru/open_ministry/anti/
            return False
    return True


def web_link_is_absolutely_prohibited(logger, source, href):
    if len(href) == 0:
        return True

    #http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278
    #href = "/bitrix/redirect.php?event1=catalog_out&amp;event2=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf&amp;event3=%D0%9F%D0%B5%D1%87%D0%B5%D0%BD%D0%B5%D0%B2%D0%B0+%D0%9D%D0%98.pdf&amp;goto=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf" > Загрузить < / a > < / b > < br / >
    #if href.find('redirect') != -1:
    #    return True

    if not check_href_elementary(href):
        return True
    if source.strip('/') == href.strip('/'):
        return True
    if href.find(' ') != -1 or href.find('\n') != -1 or href.find('\t') != -1:
        return True
    if href.find('print=') != -1:
        return True
    href_domain = get_site_domain_wo_www(href)
    source_domain = get_site_domain_wo_www(source)
    if is_super_popular_domain(href_domain):
        return True
    href_domain = re.sub(':[0-9]+$', '', href_domain) # delete port
    source_domain = re.sub(':[0-9]+$', '', source_domain)  # delete port

    if get_office_domain(href_domain) != get_office_domain(source_domain) and source_domain != "127.0.0.1":
        if not are_web_mirrors(source, href):
            return True
    return False


def make_link(main_url, href):
    url = urllib.parse.urljoin(main_url, href)

    # we cannot disable html anchors because it is used as ajax requests:
    # https://developers.google.com/search/docs/ajax-crawling/docs/specification?csw=1
    # see an example of ajax urls in
    # 1. http://minpromtorg.gov.ru/open_ministry/anti/activities/info/
    #    -> https://minpromtorg.gov.ru/docs/#!svedeniya_o_dohodah_rashodah_ob_imushhestve_i_obyazatelstvah_imushhestvennogo_haraktera_federalnyh_gosudarstvennyh_grazhdanskih_sluzhashhih_minpromtorga_rossii_rukovodstvo_a_takzhe_ih_suprugi_supruga_i_nesovershennoletnih_detey_za_period_s_1_yanvarya_2019_g_po_31_dekabrya_2019_g
    # 2. https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/4/2
    #    -> https://minzdrav.gov.ru/ministry/61/0/materialy-po-deyatelnosti-departamenta/combating_corruption/6/4/2#downloadable
    #i = url.find('#')
    #if i != -1:
    #    url = url[0:i]
    return url


def get_base_url(main_url, soup):
    for l in soup.findAll('base'):
        href = l.attrs.get('href')
        if href is not None:
            return href
    return main_url


class TRobotStep:
    panic_mode_url_count = 600
    max_step_url_count = 800

    def __init__(self, website, step_passport, init_json=None):
        self.website = website
        self.logger = website.logger
        self.step_passport = step_passport
        self.profiler = dict()
        self.step_urls = defaultdict(float)
        # runtime members
        self.processed_pages = None
        self.pages_to_process = dict()
        self.last_processed_url_weights = None
        self.second_pass = False

        if init_json is not None:
            step_urls = init_json.get('step_urls')
            if isinstance(step_urls, list):
                self.step_urls.update(dict((k, TLinkInfo.MINIMAL_LINK_WEIGHT) for k in step_urls))
            else:
                assert (isinstance(step_urls, dict))
                self.step_urls.update(step_urls)
            self.profiler = init_json.get('profiler', dict())

    def get_step_name(self):
        return self.step_passport['step_name']

    def is_last_step(self):
        return self.get_step_name() == self.website.parent_project.robot_step_passports[-1]['step_name']

    def delete_url_mirrors_by_www_and_protocol_prefix(self):
        mirrors = defaultdict(list)
        for u in self.step_urls:
            m = TUrlMirror(u)
            mirrors[m.normalized_url].append(m)
        new_step_urls = defaultdict(float)
        for urls in mirrors.values():
            urls = sorted(urls, key=(lambda x: len(x.input_url)))
            max_weight = max(self.step_urls[u.input_url] for u in urls)
            new_step_urls[urls[-1].input_url] = max_weight  # get the longest url and max weight
        self.step_urls = new_step_urls

    def to_json(self):
        return {
            'step_name': self.get_step_name(),
            'step_urls': dict((k, v) for (k, v)  in self.step_urls.items()),
            'profiler': self.profiler
        }

    def normalize_and_check_link(self, link_info: TLinkInfo):
        if link_info.target_url is not None:
            link_info.target_url = strip_viewer_prefix(link_info.target_url).strip(" \r\n\t")
            if web_link_is_absolutely_prohibited(self.logger, link_info.source_url, link_info.target_url):
                return False
        self.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.element_index,
                prepare_for_logging(link_info.target_url), # not redirected yet
                prepare_for_logging(link_info.anchor_text)))
        try:
            if self.second_pass:
                return self.step_passport['check_link_func_2'](self.logger, link_info)
            else:
                return self.step_passport['check_link_func'](self.logger, link_info)
        except UnicodeEncodeError as exp:
            self.logger.debug(exp)
            return False

    def add_link_wrapper(self, link_info: TLinkInfo):
        assert link_info.target_url is not None
        try:
            downloaded_file = TDownloadedFile(link_info.target_url)
        except THttpRequester.RobotHttpException as err:
            self.logger.error(err)
            return

        href = link_info.target_url

        self.website.url_nodes[link_info.source_url].add_child_link(href, link_info.to_json())
        link_info.weight = max(link_info.weight, self.step_urls[href])
        self.step_urls[href] = link_info.weight

        if href not in self.website.url_nodes:
            if link_info.target_title is None and downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                link_info.target_title = get_html_title(downloaded_file.data)
            self.website.url_nodes[href] = TUrlInfo(title=link_info.target_title, step_name=self.get_step_name())

        self.website.url_nodes[href].parent_nodes.add(link_info.source_url)

        if self.is_last_step():
            self.website.export_env.export_file_if_relevant(downloaded_file, link_info)

        if self.step_passport.get('transitive', False):
            if href not in self.processed_pages:
                if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                    self.pages_to_process[href] = link_info.weight

        self.logger.debug("add link {} weight={}".format(href, link_info.weight))

    def add_downloaded_file_wrapper(self, link_info: TLinkInfo):
        self.website.url_nodes[link_info.source_url].add_downloaded_file(link_info)
        if self.is_last_step():
            self.website.export_env.export_selenium_doc_if_relevant(link_info)

    def get_check_func_name(self):
        if self.second_pass:
            return self.step_passport['check_link_func_2'].__name__
        else:
            return self.step_passport['check_link_func'].__name__

    def add_page_links(self, url, use_selenium=True, use_urllib=True):
        html_parser = None
        already_processed_by_urllib = None
        downloaded_file = None
        if use_urllib:
            try:
                downloaded_file = TDownloadedFile(url)
            except THttpRequester.RobotHttpException as err:
                self.logger.error(err)
                return
            if downloaded_file.file_extension != DEFAULT_HTML_EXTENSION:
                return
            try:
                html_parser = THtmlParser(downloaded_file.data)
                already_processed_by_urllib = self.website.find_a_web_page_with_a_similar_html(self, url, html_parser.html_text)
            except Exception as e:
                self.logger.error('cannot parse html, exception {}'.format(url, e))
                return

        try:
            if use_urllib and already_processed_by_urllib is None:
                self.find_links_in_html_by_text(url, html_parser)
            else:
                if use_urllib:
                    self.logger.debug(
                        'skip processing {} in find_links_in_html_by_text, a similar file is already processed on this step: {}'.format(url, already_processed_by_urllib))

                if not use_selenium and (html_parser is None or len(list(html_parser.soup.findAll('a'))) < 10):
                    self.logger.debug('temporal switch on selenium, since this file can be fully javascripted')
                    use_selenium = True

            if use_selenium:  # switch off selenium is almost a panic mode (too many links)
                if downloaded_file is not None and downloaded_file.get_file_extension_only_by_headers() != DEFAULT_HTML_EXTENSION:
                    # selenium reads only http headers, so downloaded_file.file_extension can be DEFAULT_HTML_EXTENSION
                    self.logger.debug("do not browse {} with selenium, since it has wrong http headers".format(url))
                else:
                    self.click_all_selenium(url, self.website.parent_project.selenium_driver)
        except (THttpRequester.RobotHttpException, WebDriverException, InvalidSwitchToTargetException) as e:
            self.logger.error('add_links failed on url={}, exception: {}'.format(url, e))

    def pop_url_with_max_weight(self, url_index):
        if len(self.pages_to_process) == 0:
            return None
        enough_crawled_urls = url_index > 200 or (url_index > 100 and max(self.last_processed_url_weights[-10:]) < TLinkInfo.NORMAL_LINK_WEIGHT)
        if not self.website.check_crawling_timeouts(enough_crawled_urls):
            return None
        max_weight = TLinkInfo.MINIMAL_LINK_WEIGHT - 1.0
        best_url = None
        for url, weight in self.pages_to_process.items():
            if weight >= max_weight or best_url is None:
                max_weight = weight
                best_url = url
        if best_url is None:
            return None
        self.processed_pages.add(best_url)
        del self.pages_to_process[best_url]
        self.last_processed_url_weights.append(max_weight)
        self.logger.debug("max weight={}, index={}/{}, url={} function={}".format(
            max_weight, url_index, len(self.pages_to_process.keys()), best_url, self.get_check_func_name()))
        return best_url

    def find_links_in_html_by_text(self, main_url, html_parser: THtmlParser):
        base = get_base_url(main_url, html_parser.soup)
        if base.startswith('/'):
            base = make_link(main_url, base)
        element_index = 0
        links_to_process = list(html_parser.soup.findAll('a'))
        self.logger.debug("find_links_in_html_by_text url={} links_count={}".format(main_url, len(links_to_process)))
        for html_link in links_to_process[:MAX_LINKS_ON_ONE_WEB_PAGE]:
            href = html_link.attrs.get('href')
            if href is not None:
                element_index += 1
                link_info = TLinkInfo(TClickEngine.urllib, main_url, make_link(base, href),
                                      source_html=html_parser.html_text, anchor_text=html_link.text,
                                      tag_name=html_link.name,
                                      element_index=element_index, element_class=html_link.attrs.get('class'),
                                      source_page_title=html_parser.page_title)
                if self.normalize_and_check_link(link_info):
                    self.add_link_wrapper(link_info)

        for frame in html_parser.soup.findAll('iframe')[:MAX_LINKS_ON_ONE_WEB_PAGE]:
            href = frame.attrs.get('src')
            if href is not None:
                element_index += 1
                link_info = TLinkInfo(TClickEngine.urllib, main_url, make_link(base, href),
                                      source_html=html_parser.html_text, anchor_text=frame.text, tag_name=frame.name,
                                      element_index=element_index, source_page_title=html_parser.page_title)
                if self.normalize_and_check_link(link_info):
                    self.add_link_wrapper(link_info)

    def click_selenium_if_no_href(self, main_url, driver_holder, element, element_index):
        tag_name = element.tag_name
        link_text = element.text.strip('\n\r\t ')  # initialize here, can be broken after click
        page_html = driver_holder.the_driver.page_source
        THttpRequester.consider_request_policy(main_url + " elem_index=" + str(element_index), "click_selenium")

        link_info = TLinkInfo(TClickEngine.selenium, main_url, None,
                              source_html=page_html, anchor_text=link_text, tag_name=tag_name,
                              element_index=element_index,
                              source_page_title=driver_holder.the_driver.title)

        driver_holder.click_element(element, link_info)

        if self.normalize_and_check_link(link_info):
            if link_info.downloaded_file is not None:
                self.add_downloaded_file_wrapper(link_info)
            elif link_info.target_url is not None:
                self.add_link_wrapper(link_info)

    def click_all_selenium(self, main_url, driver_holder):
        self.logger.debug("find_links_with_selenium url={} ".format(main_url))
        THttpRequester.consider_request_policy(main_url, "GET_selenium")
        elements = driver_holder.navigate_and_get_links(main_url)
        page_html = driver_holder.the_driver.page_source
        self.logger.debug("html_size={}, elements_count={}".format(len(page_html), len(elements)))
        for element_index in range(len(elements)):
            if element_index >= MAX_LINKS_ON_ONE_WEB_PAGE:
                break
            element = elements[element_index]
            link_text = element.text.strip('\n\r\t ') if element.text is not None else ""
            if len(link_text) == 0:
                continue

            #temp debug
            #self.logger.debug("index={} text={} href={}".format(
            #    element_index,
            #    link_text,
            #    element.get_attribute('href')))

            href = element.get_attribute('href')
            if href is not None:
                href = make_link(main_url, href)  # may be we do not need it in selenium?
                link_info = TLinkInfo(TClickEngine.selenium,
                                      main_url, href,
                                      source_html=page_html, anchor_text=link_text,
                                      tag_name=element.tag_name, element_index=element_index,
                                      source_page_title=driver_holder.the_driver.title)

                if self.normalize_and_check_link(link_info):
                    self.add_link_wrapper(link_info)
            else:
                only_anchor_text = TLinkInfo(
                    TClickEngine.selenium, main_url, None,
                    source_html=page_html, anchor_text=link_text,
                    source_page_title=driver_holder.the_driver.title)
                if self.normalize_and_check_link(only_anchor_text):
                    self.logger.debug("click element {}".format(element_index))
                    try:
                        self.click_selenium_if_no_href(main_url, driver_holder, element, element_index)
                        elements = driver_holder.get_buttons_and_links()
                    except (WebDriverException, InvalidSwitchToTargetException) as exp:
                        self.logger.error("exception: {}, try restart and get the next element".format(str(exp)))
                        driver_holder.restart()
                        elements = driver_holder.navigate_and_get_links(main_url)

    def signal_alarm_handler(signum, frame):
        raise OnePageProcessingTimeoutException()

    def make_one_step(self):
        assert len(self.pages_to_process) > 0
        self.last_processed_url_weights = list()
        use_selenium = self.step_passport.get('fallback_to_selenium', True)
        if not self.website.parent_project.enable_selenium:
            use_selenium = False
        use_urllib = self.step_passport.get('use_urllib', True)
        if not self.website.enable_urllib:
            use_urllib = False
        for url_index in range(TRobotStep.max_step_url_count):
            url = self.pop_url_with_max_weight(url_index)
            if url is None:
                break
            try:
                signal.signal(signal.SIGALRM, TRobotStep.signal_alarm_handler)
                signal.alarm(THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME)
                self.add_page_links(url, use_selenium, use_urllib)
            except OnePageProcessingTimeoutException as exp:
                self.logger.error("OnePageProcessingTimeoutException, timeout is {} seconds".format(
                    THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME
                ))
            finally:
                self.logger.debug("disable signal alarm")
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                signal.alarm(0)

            if use_selenium and len(self.step_urls.keys()) >= TRobotStep.panic_mode_url_count:
                use_selenium = False
                self.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                    TRobotStep.panic_mode_url_count))
