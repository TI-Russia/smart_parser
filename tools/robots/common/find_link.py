import os
import logging
import urllib
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
from robots.common.download import  read_from_cache_or_download
from robots.common.popular_sites import is_super_popular_domain
from robots.common.http_request import consider_request_policy
from robots.common.primitives import strip_viewer_prefix, get_site_domain_wo_www


class TClickEngine:
    urllib = 'urllib'
    selenium = 'selenium'
    google = 'google'
    manual = 'manual'


class TLinkInfo:
    def __init__(self, engine, page_html, anchor_text, source=None, target=None, tag_name=None):
        self.Engine = engine
        self.PageHtml = "" if page_html is None else page_html
        self.SourceUrl = source
        if target is not None:
            self.TargetUrl = strip_viewer_prefix(target).strip(" \r\n\t")
        else:
            self.TargetUrl = None
        self.AnchorText = ""
        self.set_anchor_text(anchor_text)
        self.TagName = tag_name
        self.AnchorTextFoundSomewhere = False
        self.DownloadedFile = None
        self.TargetTitle = None
        self.AdditFeatures = dict()

    def set_anchor_text(self, anchor_text):
        self.AnchorText = '' if anchor_text is None else anchor_text.strip(" \r\n\t")

    def to_json(self):
        rec = {
            'text': self.AnchorText,
            'engine': self.Engine,
        }
        if self.TagName is not None:
            rec['tagname'] = self.TagName
        if self.AnchorTextFoundSomewhere:
            rec['text_proxim'] = True
        if self.DownloadedFile is not None:
            rec['downloaded_file'] = self.DownloadedFile
        rec.update(self.AdditFeatures)
        return rec


def are_web_mirrors(domain1, domain2):
    try:
        html1 = read_from_cache_or_download(domain1)
        html2 = read_from_cache_or_download(domain2)
        res = len(html1) == len(html2) # it is enough
        return res
    except urllib.error.URLError as exp:
        return False


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
    if href.startswith('consultantplus:'):
        return False
    if href.startswith('#'):
        if not href.startswith('#!'): # it is a hashbang (a starter for AJAX url) http://minpromtorg.gov.ru/open_ministry/anti/
            return False
    return True


def web_link_is_absolutely_prohibited(source, href):
    if href is None:
        return False  # unknown result for clicking by an element without href
    if len(href) == 0:
        return True
    if href.find('redirect') != -1:
        return True
    if check_href_elementary(href):
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
    if get_office_domain(href_domain) != get_office_domain(source_domain):
        if not are_web_mirrors(source_domain, href_domain):
            return True
    return False


def make_link(main_url, href):
    url = urllib.parse.urljoin(main_url, href)
    # see http://minpromtorg.gov.ru/open_ministry/anti/activities/info/
    #i = url.find('#')
    #if i != -1:
    #    url = url[0:i]
    return url


def can_be_office_document(href):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    filename, file_extension = os.path.splitext(href)
    if file_extension == DEFAULT_HTML_EXTENSION:
        return False
    if file_extension.lower() in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        return True
    if href.find('docs.google') != -1:
        return True
    return False


def get_base_url(main_url, soup):
    for l in soup.findAll('base'):
        href = l.attrs.get('href')
        if href is not None:
            return href
    return main_url


def prepare_for_logging(s):
    if s is None:
        return ""
    s = s.translate(str.maketrans(
        {"\n": " ",
         "\t": " ",
         "\r": " "}))
    return s.strip()


def get_soup_title(soup):
    if soup.title is None:
        return ""
    if soup.title.string is None:
        return ""
    return soup.title.string


def find_links_in_html_by_text(step_info, main_url, soup):
    logger = logging.getLogger("dlrobot_logger")
    if can_be_office_document(main_url):
        return
    base = get_base_url(main_url, soup)
    if base.startswith('/'):
        base = make_link(main_url, base)
    logger.debug("find_links_in_html_by_text url={} function={}".format(
        main_url, step_info.step_passport['check_link_func'].__name__))
    page_html = str(soup)
    element_index = 0
    for l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            element_index += 1
            if not check_href_elementary(href):
                continue
            logger.debug("check link {} {}, \"{}\"".format(element_index, prepare_for_logging(href), prepare_for_logging(l.text)))
            link_info = TLinkInfo(TClickEngine.urllib, page_html, l.text, main_url, make_link(base, href), l.name)
            if step_info.check_link_func(link_info):
                step_info.add_link_wrapper(link_info)

    for l in soup.findAll('iframe'):
        href = l.attrs.get('src')
        if href is not None:
            if not check_href_elementary(href):
                continue
            element_index += 1
            link_info = TLinkInfo(TClickEngine.urllib, page_html, l.text, main_url, make_link(base, href), l.name)
            logger.debug("check link {} {}, \"{}\"".format(element_index, prepare_for_logging(href),
                                                           prepare_for_logging(l.text)))
            if step_info.check_link_func(link_info):
                step_info.add_link_wrapper(link_info)


def click_selenium_if_no_href(step_info, main_url, driver_holder,  element, element_index):
    tag_name = element.tag_name
    link_text = element.text.strip('\n\r\t ')  # initialize here, can be broken after click
    page_html = driver_holder.the_driver.page_source
    consider_request_policy(main_url + " elem_index=" + str(element_index), "click_selenium")

    driver_holder.click_element(element)
    link_info = TLinkInfo(TClickEngine.selenium,
                          page_html,
                          link_text,
                          main_url,
                          driver_holder.the_driver.current_url,
                          tag_name)
    link_info.DownloadedFile = driver_holder.last_downloaded_file
    link_info.TargetTitle = driver_holder.the_driver.title
    driver_holder.close_window_tab()

    if step_info.check_link_func(link_info):
        if link_info.DownloadedFile is not None:
            link_info.AdditFeatures['element_index'] = element_index
            step_info.add_downloaded_file_wrapper(link_info)
        else:
            step_info.add_link_wrapper(link_info)


def click_all_selenium(step_info, main_url, driver_holder):
    logger = step_info.website.logger
    logger.debug("find_links_with_selenium url={0} , function={1}".format(main_url, step_info.check_link_func.__name__))
    consider_request_policy(main_url, "GET_selenium")
    elements = driver_holder.navigate_and_get_links(main_url)
    page_html = driver_holder.the_driver.page_source
    for i in range(len(elements)):
        element = elements[i]
        link_text = element.text.strip('\n\r\t ') if element.text is not None else ""
        if len(link_text) == 0:
            continue
        href = element.get_attribute('href')
        if href is not None:
            logger.debug("check element {}, url={} text={}".format(i, prepare_for_logging(href), prepare_for_logging(link_text)))
            href = make_link(main_url, href) # may be we do not need it in selenium?
            link_info = TLinkInfo(TClickEngine.selenium, page_html, link_text, main_url, href, element.tag_name)
            if step_info.check_link_func(link_info):
                step_info.add_link_wrapper(link_info)
        else:
            logger.debug("check element {} before click with text={}".format(i, prepare_for_logging(link_text)))
            if step_info.check_link_func(TLinkInfo(TClickEngine.selenium, page_html, link_text)):
                logger.debug("click element {} with text={}".format(i, prepare_for_logging(link_text)))
                click_selenium_if_no_href(step_info, main_url, driver_holder,  element, i)
                elements = driver_holder.get_buttons_and_links()


