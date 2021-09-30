from common.download import TDownloadedFile, DEFAULT_HTML_EXTENSION, have_the_same_content_length, \
            get_file_extension_only_by_headers, TDownloadEnv
from common.primitives import prepare_for_logging
from common.urllib_parse_pro import get_site_domain_wo_www, urlsplit_pro
from common.html_parser import THtmlParser, get_html_title
from common.link_info import TLinkInfo, TClickEngine
from common.http_request import THttpRequester
from common.popular_sites import is_super_popular_domain
from common.serp_parser import SearchEngine, SearchEngineEnum, SerpException
from common.primitives import normalize_and_russify_anchor_text
from dl_robot.declaration_link import looks_like_a_declaration_link_without_cache, best_declaration_regex_match
from common.content_types import is_video_or_audio_file_extension
from web_site_db.url_info import TUrlInfo
from common.languages import is_human_language

from selenium.common.exceptions import WebDriverException, InvalidSwitchToTargetException
from collections import defaultdict
import signal
import time
import hashlib
import re
from usp.tree import sitemap_tree_for_homepage
import urllib.parse
from operator import itemgetter

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


def check_common_domain(web_domain1, web_domain2):
    web_domain1 = web_domain1.lower()
    web_domain2 = web_domain2.lower()
    domains1 = list(web_domain1.split("."))
    domains2 = list(web_domain2.split("."))
    domains1.reverse()
    domains2.reverse()
    pairs = list(zip(domains1, domains2))
    common_domains_cnt = 0
    for i1, i2 in pairs:
        if i1 != i2:
            break
        else:
            common_domains_cnt += 1
    min_common_domains_count = 2
    if web_domain1.endswith("gov.ru") or web_domain2.endswith("gov.ru"):
        min_common_domains_count = 3

    return common_domains_cnt >= min_common_domains_count


def check_href_elementary(href):
    if len(href) == 0:
        return False
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
    # spaces are not prohibited, but should be converted
    if href.find('\n') != -1 or href.find('\t') != -1:
        return False
    if href.startswith('#'):
        if not href.startswith('#!'): # it is a hashbang (a starter for AJAX url) http://minpromtorg.gov.ru/open_ministry/anti/
            return False
    if href.find('?') != -1:
        o = urlsplit_pro(href)
        if o.query != '':
            query = urllib.parse.parse_qs(o.query)
            if 'print' in query:
                return False
            # khabkrai.ru
            if 'special' in query.get('version', list()):
                return False
            # admkrsk.ru
            if 'accessability' in query:
                return False

    return True


class OnePageProcessingTimeoutException(Exception):
    pass


def signal_alarm_handler(signum, frame):
    raise OnePageProcessingTimeoutException()


class TRobotStep:
    max_step_url_count = 800
    check_local_address = False
    selenium_timeout = 6

    def __init__(self, website, step_name=None, step_urls=None, max_links_from_one_page=1000000,
                 transitive=False, is_last_step=False,
                 check_link_func=None, include_sources=None, check_link_func_2=None, search_engine=None,
                 sitemap_xml_processor=None, profiler=None):
        self.website = website
        self.logger = website.logger
        self.step_name = step_name
        self.url_to_weight = dict() if step_urls is None else step_urls
        self.transitive = transitive
        self.check_link_func = check_link_func
        self.check_link_func_2 = check_link_func_2
        self.search_engine = dict() if search_engine is None else search_engine
        self.include_sources = include_sources
        self.sitemap_xml_processor = sitemap_xml_processor
        self.is_last_step = is_last_step
        # see https://sutr.ru/about_the_university/svedeniya-ob-ou/education/ with 20000 links
        # see https://www.gov.spb.ru/sitemap/ with 8000 links (and it is normal for great web sites)
        self.max_links_from_one_page = max_links_from_one_page
        self.profiler = dict() if profiler is None else profiler
        self.declaration_links_cache = dict()

        # runtime members
        self.processed_pages = set()
        self.pages_to_process = dict()
        self.last_processed_url_weights = list()
        self.urllib_html_cache = dict()
        self.intermediate_pdf_conversion_time_stamp = time.time()
        self.unique_hrefs = set()
        self.crawled_web_pages_count = 0
        self.start_time = time.time()

    def get_selenium_driver(self):
        return self.website.parent_project.selenium_driver

    def need_search_engine_before(self):
        return self.website.parent_project.enable_search_engine and  \
                self.search_engine.get('policy') == "run_always_before"

    def delete_url_mirrors_by_www_and_protocol_prefix(self):
        mirrors = defaultdict(list)
        for u in self.url_to_weight:
            m = TUrlMirror(u)
            mirrors[m.normalized_url].append(m)
        new_step_urls = dict()
        for urls in mirrors.values():
            urls = sorted(urls, key=(lambda x: len(x.input_url)))
            max_weight = max(self.url_to_weight.get(u.input_url, 0.0) for u in urls)
            new_step_urls[urls[-1].input_url] = max_weight  # get the longest url and max weight
        self.url_to_weight = new_step_urls

    def can_follow_this_link(self, link_info: TLinkInfo):
        source_url = link_info.source_url
        target_url = link_info.target_url
        if target_url is None:
            return True
        if not check_href_elementary(target_url):
            return False
        if source_url.strip('/') == target_url.strip('/'):
            return False

        # http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278
        # target_url = "/bitrix/redirect.php?event1=catalog_out&amp;event2=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf&amp;event3=%D0%9F%D0%B5%D1%87%D0%B5%D0%BD%D0%B5%D0%B2%D0%B0+%D0%9D%D0%98.pdf&amp;goto=%2Fupload%2Fiblock%2Fb59%2Fb59f80e6eaf7348f74e713219c169a24.pdf" > Загрузить < / a > < / b > < br / >
        # if target_url.find('redirect') != -1:
        #    return True

        href_domain = get_site_domain_wo_www(target_url)
        source_domain = get_site_domain_wo_www(source_url)
        if is_super_popular_domain(href_domain):
            return False
        href_domain = re.sub(':[0-9]+$', '', href_domain)  # delete port
        source_domain = re.sub(':[0-9]+$', '', source_domain)  # delete port
        if source_domain == href_domain:
            return True
        if check_common_domain(source_domain, href_domain):
            return True
        if TRobotStep.check_local_address:
            return True
        for redirect in self.website.parent_project.web_sites_db.get_mirrors(source_domain):
            if check_common_domain(redirect, href_domain):
                return True
        for redirect in self.website.parent_project.web_sites_db.get_mirrors(href_domain):
            if check_common_domain(source_domain, redirect):
                return True

        return False

    def to_json(self):
        return {
            'step_name': self.step_name,
            'step_urls': self.url_to_weight,
            'profiler': self.profiler
        }

    def check_link_sitemap(self, link_info: TLinkInfo):
        text = normalize_and_russify_anchor_text(link_info.anchor_text)
        return text.startswith('карта сайта') or \
                text.startswith('структура') or  \
                text.startswith('органы администрации')

    def check_anticorr_link_text(self, link_info: TLinkInfo):
        text = link_info.anchor_text.strip().lower()
        if text.find('антикоррупционная комиссия') != -1:
            link_info.weight = TLinkInfo.BEST_LINK_WEIGHT
            return True

        if text.startswith(u'противодействие') or text.startswith(u'борьба') or text.startswith(u'нет'):
            if text.find("коррупц") != -1:
                link_info.weight = TLinkInfo.BEST_LINK_WEIGHT
                return True

        text = link_info.anchor_text.strip().lower()
        if text.find("отчеты") != -1:
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            return True
        return False

    def looks_like_a_declaration_link(self, link_info: TLinkInfo):
        # return looks_like_a_declaration_link_without_cache(self.logger, link_info)
        if link_info.is_hashable():
            result = self.declaration_links_cache.get(link_info.hash_by_target())
            if result is not None:
                return result
        result = looks_like_a_declaration_link_without_cache(self.logger, link_info)
        if link_info.is_hashable():
            self.declaration_links_cache[link_info.hash_by_target()] = result
        return result

    def normalize_and_check_link(self, link_info: TLinkInfo, check_link_func):
        self.logger.debug(
            "check element {}, url={} text={}".format(
                link_info.element_index,
                prepare_for_logging(link_info.target_url), # not redirected yet
                prepare_for_logging(link_info.anchor_text)))
        try:
            #language codes
            if is_human_language(link_info.anchor_text):
                self.logger.debug("skip language link {}".format(link_info.anchor_text))
                return False
            if link_info.target_url is not None:
                file_extension = get_file_extension_only_by_headers(link_info.target_url)
                if is_video_or_audio_file_extension(file_extension):
                    self.logger.debug("link {} looks like a media file, skipped".format(link_info.target_url))
                    return False
            if not check_link_func(self, link_info):
                return False
            else:
                self.logger.debug("link {} passed {}".format(prepare_for_logging(link_info.anchor_text), check_link_func.__name__))
                return True
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
        depth = self.website.url_nodes[link_info.source_url].depth + 1

        if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
            html = downloaded_file.convert_html_to_utf8().lower()
            best_match_count = best_declaration_regex_match(html, from_start=False)
            if best_match_count > 0:
                add_weight = best_match_count * TLinkInfo.NORMAL_LINK_WEIGHT
                self.logger.debug("add weight {} to {} using best_declaration_regex_match".format(
                    add_weight, link_info.weight))
                link_info.weight += add_weight
        if depth < 15:
            link_info.weight -= 0.1 * depth
        elif depth < 30:
            link_info.weight -= 0.5 * depth
        else:
            link_info.weight -= 6.0 * depth

        link_info.weight = max(link_info.weight, self.url_to_weight.get(href, 0.0))
        self.url_to_weight[href] = link_info.weight

        if href not in self.website.url_nodes:
            if link_info.target_title is None and downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                link_info.target_title = get_html_title(downloaded_file.data)
            self.website.url_nodes[href] = TUrlInfo(title=link_info.target_title, step_name=self.step_name, depth=depth,
                                                    parent_node=link_info.source_url)
        else:
            self.website.url_nodes[href].add_parent_node(link_info.source_url)
            self.website.url_nodes[href].update_depth(depth)

        if self.is_last_step:
            self.website.export_env.export_file_if_relevant(downloaded_file, link_info)

        if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
            if self.website.export_env.sha256_is_exported(downloaded_file.get_sha256()):
                link_info.weight = TLinkInfo.MINIMAL_LINK_WEIGHT
                self.logger.debug("set weight {} to an html declaration".format(link_info.weight))

        if self.transitive:
            if href not in self.processed_pages:
                if downloaded_file.file_extension == DEFAULT_HTML_EXTENSION:
                    self.pages_to_process[href] = link_info.weight

        if href in self.pages_to_process:
            self.pages_to_process[href] = max(self.pages_to_process[href], link_info.weight)

        self.logger.debug("add link {} weight={}".format(href, link_info.weight))

    def add_downloaded_file_wrapper(self, link_info: TLinkInfo):
        self.website.url_nodes[link_info.source_url].add_downloaded_file(link_info)
        if self.is_last_step:
            self.website.export_env.export_selenium_doc_if_relevant(link_info)

    def add_downloaded_file_manually(self, downloaded_file: TDownloadedFile, href=None, declaration_year=None):
        if href is None:
            href = self.website.main_page_url
        link_info = TLinkInfo(TClickEngine.selenium, self.website.main_page_url, href,
                              source_html="", anchor_text="", tag_name="a",
                              element_index=1, downloaded_file=downloaded_file,
                              declaration_year=declaration_year)
        self.add_downloaded_file_wrapper(link_info)

    def add_page_links_selenium(self, url, check_link_func):
        try:
            ext = get_file_extension_only_by_headers(url)
            if ext == DEFAULT_HTML_EXTENSION or ext is None:
                # selenium reads only http headers, so url must be an html file,
                # ext is None  if http  head request failed and we do not know file type
                self.click_all_selenium(url, check_link_func)
            else:
                self.logger.debug("do not browse {} with selenium, since it does not look like an html file".format(url))
        except (THttpRequester.RobotHttpException, WebDriverException) as e:
            self.logger.error('add_page_links_selenium failed on url={}, exception: {}'.format(url, e))

    def add_page_links(self, url, check_link_func):
        self.add_page_links_selenium(url, check_link_func)

    def pop_url_with_max_weight(self, url_index):
        if len(self.pages_to_process) == 0:
            return None
        robot_speed = 60.0 * self.website.export_env.found_declarations_count / (time.time() - self.start_time)
        #significiant_crawled_urls = self.crawled_web_pages_count > 200 or \
        #                      (self.crawled_web_pages_count > 100 and max(self.last_processed_url_weights[-10:]) < TLinkInfo.NORMAL_LINK_WEIGHT)
        if not self.website.check_crawling_timeouts(robot_speed, self.crawled_web_pages_count):
            return None
        best_url, max_weight = max(self.pages_to_process.items(), key=itemgetter(1))
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
                if self.can_follow_this_link(link_info):
                    if self.normalize_and_check_link(link_info, check_link_func):
                        self.add_link_wrapper(link_info)

        for frame in html_parser.soup.findAll('iframe')[:self.max_links_from_one_page]:
            href = frame.attrs.get('src')
            if href is not None:
                element_index += 1
                link_info = TLinkInfo(TClickEngine.urllib, main_url, html_parser.make_link_soup(href),
                                      source_html=html_parser.html_with_markup, anchor_text=frame.text, tag_name=frame.name,
                                      element_index=element_index, source_page_title=html_parser.page_title)
                if self.can_follow_this_link(link_info):
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

    def link_must_be_clicked(self, link_info: TLinkInfo):
        return re.search('скачать', link_info.anchor_text, re.IGNORECASE) is not None

    def build_link_info(self, main_url, page_html, element_index, element, html_title):
        link_text = element['anchor'].strip('\n\r\t ') if element['anchor'] is not None else ""

        return TLinkInfo(TClickEngine.selenium,
                              source_url=main_url,
                              target_url=element['href'],
                              source_html=page_html,
                              anchor_text=link_text,
                              tag_name=element['id'].tag_name,
                              element_index=element_index,
                              element_class=[element.get('class')],
                              source_page_title=html_title)

    def process_selenium_element(self, link_info: TLinkInfo, element, check_link_func):
        if link_info.element_index >= self.max_links_from_one_page:
            return
        if not self.normalize_and_check_link(link_info, check_link_func):
            return
        if link_info.target_url is None or self.link_must_be_clicked(link_info):
            try:
                self.logger.debug("click element {}".format(link_info.element_index))
                self.click_selenium_if_no_href(link_info.source_url, element['id'], link_info.element_index, check_link_func)
            except WebDriverException as exp:
                self.logger.debug("exception: {}".format(exp))
                if link_info.target_url is not None:  # see gorsovet-podolsk in tests
                    if self.normalize_and_check_link(link_info, check_link_func):
                        self.add_link_wrapper(link_info)
        else:
            self.add_link_wrapper(link_info)

    def find_languages_links(self, elements, processed_elements):
        language_links = list()
        for element_index, element, in enumerate(elements):
            if is_human_language(element['anchor']):
                language_links.append(element_index)
                processed_elements.add(element['id'])
        # a link between a language links is also a language link
        for s, e in zip(language_links, language_links[1:]):
            for i in range(s + 1, e):
                processed_elements.add(elements[i]['id'])

    def click_all_selenium(self, main_url, check_link_func):
        self.logger.debug("find_links_with_selenium url={} ".format(main_url))
        THttpRequester.consider_request_policy(main_url, "GET_selenium")
        elements = self.get_selenium_driver().navigate_and_get_links_js(main_url, TRobotStep.selenium_timeout)
        if elements is None:
            self.logger.error("cannot get child elements using javascript for url={}".format(main_url))
            return
        page_html = self.get_selenium_driver().the_driver.page_source
        if page_html is None:
            self.logger.error("cannot get html source_url for url={}".format(main_url))
            return
        self.logger.debug("html_size={}, elements_count={}".format(len(page_html), len(elements)))
        processed_elements = set()

        self.find_languages_links(elements, processed_elements)
        html_title = self.get_selenium_driver().the_driver.title
        link_infos = dict()
        not_empty_links = set()
        for element_index, element, in enumerate(elements):
            link_info = self.build_link_info(main_url, page_html, element_index, element, html_title)
            link_infos[element['id']] = link_info
            if not self.can_follow_this_link(link_info):
                processed_elements.add(element['id'])
            else:
                if link_info.target_url is not None:
                    not_empty_links.add(link_info.target_url)

        if len(not_empty_links) > 30 and not_empty_links.issubset(self.unique_hrefs):
            self.logger.debug("skip page, since its links are similar to the previous page (speed optimization)")
            return
        else:
            for x in not_empty_links:
                if x not in self.unique_hrefs:
                    pass
            self.unique_hrefs.update(not_empty_links)
            self.unique_hrefs.add(main_url)

        self.crawled_web_pages_count += 1
        for element_index, element, in enumerate(elements):
            if element['id'] not in processed_elements:
                processed_elements.add(element['id'])
                self.process_selenium_element(link_infos[element['id']], element, check_link_func)

        # получаем еще раз ссылки, может быть, что-то новое отрисовал javascript, хотя,
        # может быть, надо брать ссылки не после, а до скролдауна и сравнивать их по href, а не по id,
        # т.е. до того как javaскрипт начал скрывать их (поближе  к чистой странице, как будто мы ее скачали curl)

        elements = self.get_selenium_driver().get_links_js(timeout=TRobotStep.selenium_timeout)
        if elements is None:
            self.logger.error("cannot get child elements using javascript for url={} (second)".format(main_url))
            return
        for element_index, element, in enumerate(elements):
            if element['id'] not in processed_elements:
                link_info = self.build_link_info(main_url, page_html, element_index, element, html_title)
                if self.can_follow_this_link(link_info):
                    self.process_selenium_element(link_info, element, check_link_func)

    def intermediate_check_pdf_conversion(self):
        if TDownloadEnv.CONVERSION_CLIENT is None:
            return
        cur_time = time.time()
        if cur_time < self.intermediate_pdf_conversion_time_stamp + 60*15:   # 15 minutes
            # do not ddos conversion server
            return
        self.intermediate_pdf_conversion_time_stamp = cur_time
        completed = TDownloadEnv.CONVERSION_CLIENT.get_completed_tasks()
        for sha256 in completed:
            file_set = self.website.export_env.export_files_by_sha256.get(sha256)
            if file_set is None:
                self.logger.error('file {} cannot be found in export list')
                continue
            self.website.export_env.run_dl_recognizer_wrapper(file_set)

    def apply_function_to_links(self, check_link_func):
        assert len(self.pages_to_process) > 0
        self.last_processed_url_weights = list()
        for url_index in range(TRobotStep.max_step_url_count):
            url = self.pop_url_with_max_weight(url_index)
            if url is None:
                break
            self.intermediate_check_pdf_conversion()
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

        if url_index == TRobotStep.max_step_url_count:
            self.logger.error("this is the last url (max={}) but we have time to crawl further".format(
                TRobotStep.max_step_url_count))

    def add_regional_main_pages(self):
        for url in self.website.get_regional_pages():
            link_info = TLinkInfo(TClickEngine.manual, self.website.main_page_url, url)
            link_info.weight = TLinkInfo.NORMAL_LINK_WEIGHT
            self.add_link_wrapper(link_info)

    def add_links_from_sitemap_xml(self,  check_url_func):
        assert self.website.main_page_url in self.website.url_nodes
        root_page = self.website.main_page_url.strip('/')
        tree = sitemap_tree_for_homepage(root_page)
        cnt = 0
        useful = 0
        for page in tree.all_pages():
            cnt += 1
            weight = check_url_func(page.url)
            if weight > TLinkInfo.MINIMAL_LINK_WEIGHT:
                if page.url not in self.pages_to_process:
                    useful += 1
                    link_info = TLinkInfo(TClickEngine.sitemap_xml, self.website.main_page_url, page.url, anchor_text="")
                    link_info.weight = weight
                    self.add_link_wrapper(link_info)
        self.logger.info("processed {} links from {}/sitemap.xml found {} useful links".format(cnt, root_page, useful))

    def use_search_engine(self, morda_url):
        request = self.search_engine['request']
        max_results = self.search_engine.get('max_serp_results', 10)
        site = self.website.main_page_url
        self.logger.info('search engine request: {} site:{}'.format(request, site))
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

    def make_one_step(self, start_pages):
        self.logger.info("=== step {0} =========".format(self.step_name))
        self.logger.info(self.website.main_page_url)
        self.url_to_weight = dict()
        self.start_time = time.time()
        if self.is_last_step:
            self.website.create_export_folder()

        self.pages_to_process = dict(start_pages)
        self.processed_pages = set()

        if self.include_sources == "always":
            assert not self.is_last_step  # todo: should we export it?
            self.url_to_weight.update(self.pages_to_process)

        if self.need_search_engine_before():
            self.use_search_engine(self.website.main_page_url)
            self.pages_to_process.update(self.url_to_weight)

        if self.sitemap_xml_processor:
            self.add_links_from_sitemap_xml(self.sitemap_xml_processor.get('check_url_func'))

        self.apply_function_to_links(self.check_link_func)

        if self.step_name == "sitemap":
            self.add_regional_main_pages()

        self.profiler = {
            "elapsed_time":  time.time() - self.start_time,
            "step_request_rate": THttpRequester.get_request_rate(self.start_time),
            "site_request_rate": THttpRequester.get_request_rate()
        }
        self.logger.debug("{}".format(str(self.profiler)))
        self.delete_url_mirrors_by_www_and_protocol_prefix()
        self.logger.info('{0} source_url links -> {1} target links'.format(len(start_pages), len(self.url_to_weight)))
