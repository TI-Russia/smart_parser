from common.download import TDownloadedFile, DEFAULT_HTML_EXTENSION, are_web_mirrors
from common.primitives import prepare_for_logging, get_site_domain_wo_www, build_dislosures_sha256_by_html
from common.html_parser import THtmlParser
from common.link_info import TLinkInfo, TClickEngine
from common.primitives import get_html_title
from common.http_request import THttpRequester
from common.popular_sites import is_super_popular_domain
from common.serp_parser import SearchEngine, SearchEngineEnum, SerpException

from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
from collections import defaultdict
import signal
import time
import hashlib
import re
from usp.tree import sitemap_tree_for_homepage
import urllib.parse


#disable logging for usp.tree
import logging
for name in logging.root.manager.loggerDict:
    if name.startswith('usp.'):
        logging.getLogger(name).setLevel(logging.CRITICAL)


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


class OnePageProcessingTimeoutException(Exception):
    pass


def signal_alarm_handler(signum, frame):
    raise OnePageProcessingTimeoutException()


class TRobotStep:
    panic_mode_url_count = 600
    max_step_url_count = 800
    check_local_address = False
    selenium_timeout = 6

    def __init__(self, website, step_name=None, step_urls=None, max_links_from_one_page=1000000,
                 transitive=False, fallback_to_selenium=True, use_urllib=True, is_last_step=False,
                 check_link_func=None, include_sources=None, check_link_func_2=None, search_engine=None,
                 do_not_copy_urls_from_steps=None, sitemap_xml_processor=None, profiler=None):
        self.website = website
        self.logger = website.logger
        self.step_name = step_name
        self.step_urls = dict() if step_urls is None else step_urls
        self.transitive = transitive
        self.check_link_func = check_link_func
        self.check_link_func_2 = check_link_func_2
        self.search_engine = dict() if search_engine is None else search_engine
        self.do_not_copy_urls_from_steps = list() if do_not_copy_urls_from_steps is None else do_not_copy_urls_from_steps
        self.include_sources = include_sources
        self.sitemap_xml_processor = sitemap_xml_processor
        self.fallback_to_selenium = fallback_to_selenium and self.website.parent_project.enable_selenium
        self.use_urllib = use_urllib and self.website.enable_urllib
        self.is_last_step = is_last_step
        # see https://sutr.ru/about_the_university/svedeniya-ob-ou/education/ with 20000 links
        # see https://www.gov.spb.ru/sitemap/ with 8000 links (and it is normal for great web sites)
        self.max_links_from_one_page = max_links_from_one_page
        self.profiler = dict() if profiler is None else profiler

        # runtime members
        self.processed_pages = set()
        self.pages_to_process = dict()
        self.last_processed_url_weights = list()
        self.urllib_html_cache = dict()

    def get_selenium_driver(self):
        return self.website.parent_project.selenium_driver

    def need_search_engine_after(self):
        return self.website.parent_project.enable_search_engine and \
               self.search_engine.get('policy') == "run_after_if_no_results" and \
               len(self.step_urls) == 0

    def need_search_engine_before(self):
        return self.website.parent_project.enable_search_engine and  \
                self.search_engine.get('policy') == "run_always_before"

    def delete_url_mirrors_by_www_and_protocol_prefix(self):
        mirrors = defaultdict(list)
        for u in self.step_urls:
            m = TUrlMirror(u)
            mirrors[m.normalized_url].append(m)
        new_step_urls = dict()
        for urls in mirrors.values():
            urls = sorted(urls, key=(lambda x: len(x.input_url)))
            max_weight = max(self.step_urls.get(u.input_url, 0.0) for u in urls)
            new_step_urls[urls[-1].input_url] = max_weight  # get the longest url and max weight
        self.step_urls = new_step_urls

    def web_link_is_absolutely_prohibited(self, source, href):
        if len(href) == 0:
            return True
        if not check_href_elementary(href):
            return True
        if source.strip('/') == href.strip('/'):
            return True

        #spaces are not prohibited, but should be converted
        if href.find('\n') != -1 or href.find('\t') != -1:
            return True

        # http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278
        # href = "/bitrix/redirect.php?event1=catalog_out&amp;event2=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf&amp;event3=%D0%9F%D0%B5%D1%87%D0%B5%D0%BD%D0%B5%D0%B2%D0%B0+%D0%9D%D0%98.pdf&amp;goto=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf" > Загрузить < / a > < / b > < br / >
        # if href.find('redirect') != -1:
        #    return True

        if href.find('?'):
            o = urllib.parse.urlparse(href)
            if o.query != '':
                query = urllib.parse.parse_qs(o.query)
                if 'print' in query:
                    return True
                # khabkrai.ru
                if 'special' in query.get('version', list()):
                    return True
                # admkrsk.ru
                if 'accessability' in query:
                    return True

        href_domain = get_site_domain_wo_www(href)
        source_domain = get_site_domain_wo_www(source)
        if is_super_popular_domain(href_domain):
            return True
        href_domain = re.sub(':[0-9]+$', '', href_domain)  # delete port
        source_domain = re.sub(':[0-9]+$', '', source_domain)  # delete port

        if get_office_domain(href_domain) != get_office_domain(source_domain) and (
                not self.check_local_address or source_domain != "127.0.0.1"):
            if not are_web_mirrors(source, href):
                return True
        return False

    def to_json(self):
        return {
            'step_name': self.step_name,
            'step_urls': self.step_urls,
            'profiler': self.profiler
        }

    def normalize_and_check_link(self, link_info: TLinkInfo, check_link_func):
        if link_info.target_url is not None:
            if self.web_link_is_absolutely_prohibited(link_info.source_url, link_info.target_url):
                return False
        self.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.element_index,
                prepare_for_logging(link_info.target_url), # not redirected yet
                prepare_for_logging(link_info.anchor_text)))
        try:
            return check_link_func(self.logger, link_info)
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
        link_info.weight = max(link_info.weight, self.step_urls.get(href, 0.0))
        self.step_urls[href] = link_info.weight

        if href not in self.website.url_nodes:
            if link_info.target_title is None and downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                link_info.target_title = get_html_title(downloaded_file.data)
            self.website.url_nodes[href] = TUrlInfo(title=link_info.target_title, step_name=self.step_name)

        self.website.url_nodes[href].parent_nodes.add(link_info.source_url)

        if self.is_last_step:
            self.website.export_env.export_file_if_relevant(downloaded_file, link_info)

        if self.transitive:
            if href not in self.processed_pages:
                if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                    self.pages_to_process[href] = link_info.weight

        if href in self.pages_to_process and self.pages_to_process[href] < link_info.weight:
            self.pages_to_process[href] = link_info.weight

        self.logger.debug("add link {} weight={}".format(href, link_info.weight))

    def add_downloaded_file_wrapper(self, link_info: TLinkInfo):
        self.website.url_nodes[link_info.source_url].add_downloaded_file(link_info)
        if self.is_last_step:
            self.website.export_env.export_selenium_doc_if_relevant(link_info)

    def add_downloaded_file_manually(self, downloaded_file: TDownloadedFile, href=None, declaration_year=None):
        if href is None:
            href = self.website.morda_url
        link_info = TLinkInfo(TClickEngine.selenium, self.website.morda_url, href,
                              source_html="", anchor_text="", tag_name="a",
                              element_index=1, downloaded_file=downloaded_file,
                              declaration_year=declaration_year)
        self.add_downloaded_file_wrapper(link_info)

    def find_a_web_page_in_urllib_cache(self, url, html_text, check_link_func):
        if len(html_text) > 1000:
            html_text = re.sub('[0-9]+', 'd', html_text)
            hash_code = "{}_{}_{}".format(
                self.step_name, check_link_func.__name__, hashlib.sha256(html_text.encode("utf8")).hexdigest())
            already = self.urllib_html_cache.get(hash_code)
            if already is not None:
                return already
            self.urllib_html_cache[hash_code] = url
        return None

    def add_page_links(self, url, check_link_func):
        html_parser = None
        already_processed_by_urllib = None
        downloaded_file = None
        if self.use_urllib:
            try:
                downloaded_file = TDownloadedFile(url)
            except THttpRequester.RobotHttpException as err:
                self.logger.error(err)
                return
            if downloaded_file.file_extension != DEFAULT_HTML_EXTENSION:
                return
            try:
                html_parser = THtmlParser(downloaded_file.data, url=url)
                already_processed_by_urllib = self.find_a_web_page_in_urllib_cache(
                    url, html_parser.html_with_markup, check_link_func)
            except Exception as e:
                self.logger.error('cannot parse html url={}, exception = {}'.format(url, e))
                return

        try:
            if self.use_urllib and already_processed_by_urllib is None:
                self.find_links_in_html_by_text(url, html_parser, check_link_func)
            else:
                if self.use_urllib:
                    self.logger.debug(
                        'skip processing {} in find_links_in_html_by_text, a similar file is already processed on this step: {}'.format(url, already_processed_by_urllib))

                if not self.fallback_to_selenium and (html_parser is None or len(list(html_parser.soup.findAll('a'))) < 10):
                    self.logger.debug('temporal switch on selenium, since this file can be fully javascripted')
                    self.fallback_to_selenium = True

            if self.fallback_to_selenium:  # switch off selenium is almost a panic mode (too many links)
                if downloaded_file is not None and downloaded_file.get_file_extension_only_by_headers() != DEFAULT_HTML_EXTENSION:
                    # selenium reads only http headers, so downloaded_file.file_extension can be DEFAULT_HTML_EXTENSION
                    self.logger.debug("do not browse {} with selenium, since it has wrong http headers".format(url))
                else:
                    self.click_all_selenium(url, check_link_func)
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
        self.logger.debug("choose url {} weight={} index={} left={}".format(
            best_url, max_weight, url_index, len(self.pages_to_process.keys())))
        return best_url

    def find_links_in_html_by_text(self, main_url, html_parser: THtmlParser, check_link_func):
        element_index = 0
        links_to_process = list(html_parser.soup.findAll('a'))
        self.logger.debug("find_links_in_html_by_text url={} links_count={}".format(main_url, len(links_to_process)))
        for html_link in links_to_process[:self.max_links_from_one_page]:
            href = html_link.attrs.get('href')
            if href is not None:
                element_index += 1
                link_info = TLinkInfo(TClickEngine.urllib, main_url, html_parser.make_link_soup(href),
                                      source_html=html_parser.html_with_markup, anchor_text=html_link.text,
                                      tag_name=html_link.name,
                                      element_index=element_index, element_class=html_link.attrs.get('class'),
                                      source_page_title=html_parser.page_title)
                if self.normalize_and_check_link(link_info, check_link_func):
                    self.add_link_wrapper(link_info)

        for frame in html_parser.soup.findAll('iframe')[:self.max_links_from_one_page]:
            href = frame.attrs.get('src')
            if href is not None:
                element_index += 1
                link_info = TLinkInfo(TClickEngine.urllib, main_url, html_parser.make_link_soup(href),
                                      source_html=html_parser.html_with_markup, anchor_text=frame.text, tag_name=frame.name,
                                      element_index=element_index, source_page_title=html_parser.page_title)
                if self.normalize_and_check_link(link_info, check_link_func):
                    self.add_link_wrapper(link_info)

    def click_selenium_if_no_href(self, main_url, element, element_index, check_link_func):
        tag_name = element.tag_name
        link_text = element.text.strip('\n\r\t ')  # initialize here, can be broken after click
        page_html = self.get_selenium_driver().the_driver.page_source
        THttpRequester.consider_request_policy(main_url + " elem_index=" + str(element_index), "click_selenium")

        link_info = TLinkInfo(TClickEngine.selenium, main_url, None,
                              source_html=page_html, anchor_text=link_text, tag_name=tag_name,
                              element_index=element_index,
                              source_page_title=self.get_selenium_driver().the_driver.title)

        self.get_selenium_driver().click_element(element, link_info)

        if self.normalize_and_check_link(link_info, check_link_func):
            if link_info.downloaded_file is not None:
                self.add_downloaded_file_wrapper(link_info)
            elif link_info.target_url is not None:
                self.add_link_wrapper(link_info)

    def click_all_selenium(self, main_url, check_link_func):
        self.logger.debug("find_links_with_selenium url={} ".format(main_url))
        THttpRequester.consider_request_policy(main_url, "GET_selenium")
        elements = self.get_selenium_driver().navigate_and_get_links(main_url, TRobotStep.selenium_timeout)
        page_html = self.get_selenium_driver().the_driver.page_source
        self.logger.debug("html_size={}, elements_count={}".format(len(page_html), len(elements)))
        for element_index in range(len(elements)):
            if element_index >= self.max_links_from_one_page:
                break
            element = elements[element_index]
            link_text = element.text.strip('\n\r\t ') if element.text is not None else ""
            if len(link_text) == 0:
                continue
            mandatory_link = re.search('скачать', link_text, re.IGNORECASE) is not None

            #temp debug
            #self.logger.debug("index={} text={} href={}".format(
            #    element_index,
            #    link_text,
            #    element.get_attribute('href')))

            href = element.get_attribute('href')
            if href is not None and not mandatory_link:
                href = THtmlParser.make_link(main_url, href)  # may be we do not need it in selenium?
                link_info = TLinkInfo(TClickEngine.selenium,
                                      main_url, href,
                                      source_html=page_html, anchor_text=link_text,
                                      tag_name=element.tag_name, element_index=element_index,
                                      source_page_title=self.get_selenium_driver().the_driver.title)

                if self.normalize_and_check_link(link_info, check_link_func):
                    self.add_link_wrapper(link_info)
            else:
                only_anchor_text = TLinkInfo(
                    TClickEngine.selenium, main_url, None,
                    source_html=page_html, anchor_text=link_text,
                    source_page_title=self.get_selenium_driver().the_driver.title)
                if self.normalize_and_check_link(only_anchor_text, check_link_func):
                    self.logger.debug("click element {}".format(element_index))
                    try:
                        self.click_selenium_if_no_href(main_url, element, element_index, check_link_func)
                        elements = self.get_selenium_driver().get_buttons_and_links()
                    except (WebDriverException, InvalidSwitchToTargetException) as exp:
                        self.logger.error("exception: {}, try restart and get the next element".format(str(exp)))
                        self.get_selenium_driver().restart()
                        elements = self.get_selenium_driver().navigate_and_get_links(main_url, TRobotStep.selenium_timeout)

    def apply_function_to_links(self, check_link_func):
        assert len(self.pages_to_process) > 0
        self.last_processed_url_weights = list()
        for url_index in range(TRobotStep.max_step_url_count):
            url = self.pop_url_with_max_weight(url_index)
            if url is None:
                break

            try:
                signal.signal(signal.SIGALRM, signal_alarm_handler)
                signal.alarm(THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME)
                self.add_page_links(url, check_link_func)
            except OnePageProcessingTimeoutException as exp:
                self.logger.error("OnePageProcessingTimeoutException, timeout is {} seconds".format(
                    THttpRequester.WEB_PAGE_LINKS_PROCESSING_MAX_TIME
                ))
            finally:
                self.logger.debug("disable signal alarm")
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                signal.alarm(0)

            if self.fallback_to_selenium and len(self.step_urls.keys()) >= TRobotStep.panic_mode_url_count:
                self.fallback_to_selenium = False
                self.logger.error("too many links (>{}),  switch off fallback_to_selenium".format(
                    TRobotStep.panic_mode_url_count))

        if url_index == TRobotStep.max_step_url_count:
            self.logger.error("this is the last url (max={}) but we have time to crawl further".format(
                TRobotStep.max_step_url_count))

    def add_regional_main_pages(self, regional_main_pages):
        for url in regional_main_pages:
            if not url.startswith('http'):
                url = self.protocol + "://" + url
            link_info = TLinkInfo(TClickEngine.manual, self.website.morda_url, url)
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            self.add_link_wrapper(link_info)

    def add_links_from_sitemap_xml(self, morda_url, check_url_func):
        tree = sitemap_tree_for_homepage(morda_url)
        cnt = 0
        useful = 0
        for page in tree.all_pages():
            cnt += 1
            weight = check_url_func(page.url)
            if weight > TLinkInfo.MINIMAL_LINK_WEIGHT:
                if page.url not in self.pages_to_process:
                    useful += 1
                    link_info = TLinkInfo(TClickEngine.sitemap_xml, morda_url, page.url, anchor_text="")
                    link_info.weight = weight
                    self.add_link_wrapper(link_info)
        self.logger.info("processed {} links from sitemap.xml found {} useful links".format(cnt, useful))

    def use_search_engine(self, morda_url):
        request = self.search_engine['request']
        max_results = self.search_engine.get('max_serp_results', 10)
        self.logger.info('search engine request: {}'.format(request))
        site = self.website.get_domain_name()
        serp_urls = list()
        search_engine = None
        for search_engine in range(0, SearchEngineEnum.SearchEngineCount):
            try:
                serp_urls = SearchEngine.site_search(search_engine, site, request, self.get_selenium_driver())
                break
            except (SerpException, THttpRequester.RobotHttpException, WebDriverException, InvalidSwitchToTargetException) as err:
                self.logger.error('cannot request search engine, exception: {}'.format(err))
                self.logger.debug("sleep 10 seconds and retry other search engine")
                time.sleep(10)
                self.get_selenium_driver().restart()
                time.sleep(5)
                self.logger.error('retry...')

        links_count = 0
        for url in serp_urls:
            link_info = TLinkInfo(TClickEngine.google, morda_url, url, anchor_text=request)
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            self.add_link_wrapper(link_info)
            links_count += 1
            if max_results == 1:
                break  # one  link found
        self.logger.info('found {} links using search engine id={}'.format(links_count, search_engine))

    def make_one_step(self, start_pages, regional_main_pages):
        self.logger.info("=== step {0} =========".format(self.step_name))
        self.logger.info(self.website.get_domain_name())
        self.step_urls = dict()
        start_time = time.time()
        if self.is_last_step:
            self.website.create_export_folder()

        self.pages_to_process = dict(start_pages)
        self.processed_pages = set()

        if self.include_sources == "always":
            assert not self.is_last_step  # todo: should we export it?
            self.step_urls.update(self.pages_to_process)

        if self.need_search_engine_before():
            self.use_search_engine(self.website.morda_url)
            self.pages_to_process.update(self.step_urls)

        if self.sitemap_xml_processor:
            self.add_links_from_sitemap_xml(self.website.morda_url, self.sitemap_xml_processor.get('check_url_func'))

        save_input_urls = dict(self.pages_to_process.items())

        self.apply_function_to_links(self.check_link_func)

        if len(self.step_urls) == 0:
            if self.check_link_func_2:
                self.logger.debug("second pass with {}".format(self.check_link_func_2.__name__))
                self.pages_to_process = save_input_urls
                self.apply_function_to_links(self.check_link_func_2)

        if self.need_search_engine_after():
            self.use_search_engine(self.website.morda_url)

        if self.step_name == "sitemap":
            self.add_regional_main_pages(regional_main_pages)

        if self.include_sources == "copy_if_empty" and len(self.step_urls) == 0:
            for url, weight in start_pages.items():
                step_name = self.website.url_nodes[url].step_name
                if step_name not in self.do_not_copy_urls_from_steps:
                    self.step_urls[url] = weight

        self.profiler = {
            "elapsed_time":  time.time() - start_time,
            "step_request_rate": THttpRequester.get_request_rate(start_time),
            "site_request_rate": THttpRequester.get_request_rate()
        }
        self.logger.debug("{}".format(str(self.profiler)))
        self.delete_url_mirrors_by_www_and_protocol_prefix()
        self.logger.info('{0} source links -> {1} target links'.format(len(start_pages), len(self.step_urls)))
