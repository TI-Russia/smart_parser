import os
import logging
import time
import urllib
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS, DEFAULT_HTML_EXTENSION
from robots.common.download import get_site_domain_wo_www, read_from_cache_or_download
from robots.common.popular_sites import is_super_popular_domain
from robots.common.http_request import consider_request_policy


class TLinkInfo:
    def __init__(self, page_html, anchor_text, source=None, target=None, tagName=None, download_by_selenium=None):
        self.PageHtml = "" if page_html is None else page_html
        self.Source = source
        self.Target = target
        self.AnchorText = '' if anchor_text is None else anchor_text
        self.TagName = tagName
        self.DownloadedBySelenium = download_by_selenium


def strip_viewer_prefix(href):
    # https://docs.google.com/viewer?url=https%3A%2F%2Foren-rshn.ru%2Findex.php%3Fdo%3Ddownload%26id%3D247%26area%3Dstatic%26viewonline%3D1
    viewers = ['https://docs.google.com/viewer?url=',
                'https://docviewer.yandex.ru/?url=',
                'https://view.officeapps.live.com/op/embed.aspx?src=',
                'https://view.officeapps.live.com/op/view.aspx?src=']
    for prefix in viewers:
        if href.startswith(prefix):
            href = href[len(prefix):]
            return urllib.parse.unquote(href)
    return href


def are_web_mirrors(domain1, domain2):
    try:
        html1 = read_from_cache_or_download(domain1)
        html2 = read_from_cache_or_download(domain2)
        res = len(html1) == len(html2) # it is enough
        return res
    except urllib.error.URLError as exp:
        return False


def web_link_is_absolutely_prohibited(source, href):
    if href is None:
        return False  # unknown result for clicking by an element without href
    if len(href) == 0:
        return True
    if href.find('redirect') != -1:
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
    href_domains_first_2_domain = ".".join(href_domain.split(".")[-2:])
    source_domains_first_2_domain = ".".join(source_domain.split(".")[-2:])
    if href_domains_first_2_domain != source_domains_first_2_domain:
        if not are_web_mirrors(source_domain, href_domain):
            return True
    return False


def strip_html_url(url):
    if url.endswith('.html'):
        url = url[:-len('.html')]
    if url.endswith('.htm'):
        url = url[:-len('.htm')]
    if url.startswith('http://'):
        url = url[len('http://'):]
    if url.startswith('http://'):
        url = url[len('https://'):]
    if url.startswith('www.'):
        url = url[len('www.'):]
    return url


def check_sub_page_or_iframe(link_info):
    if web_link_is_absolutely_prohibited(link_info.Source, link_info.Target):
        return False
    if link_info.Target is None:
        return False
    if link_info.TagName is not None and link_info.TagName.lower() == "iframe":
        return True
    parent = strip_html_url(link_info.Source)
    subpage = strip_html_url(link_info.Target)
    return subpage.startswith(parent)


def check_anticorr_link_text(link_info):
    if web_link_is_absolutely_prohibited(link_info.Source, link_info.Target):
        return False

    text = link_info.AnchorText.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1

    return False


def make_link(main_url, href):
    url = urllib.parse.urljoin(main_url, href)
    # see http://minpromtorg.gov.ru/open_ministry/anti/activities/info/
    #i = url.find('#')
    #if i != -1:
    #    url = url[0:i]
    return url

class SomeOtherTextException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return (repr(self.value))


def find_recursive_to_bottom(page_html, start_element, check_link_func, element):
    children = element.findChildren()
    if len(children) == 0:
        if len(element.text) > 0 and element != start_element:
            if check_link_func(TLinkInfo(page_html, element.text)):
                return element.text
            if len (element.text.strip()) > 10:
                raise SomeOtherTextException(element.text.strip())
    else:
        for child in children:
            start_time = time.time()
            found_text = find_recursive_to_bottom(page_html, start_element, check_link_func, child)
            if time.time() - start_time > 10:  # skip very large html (duma-torzhok.ru)
                logging.getLogger("dlrobot_logger").error("stop  too long recursive html processing")
                raise SomeOtherTextException("")
            if len(found_text) > 0:
                return found_text
    return ""


def check_long_near_text(page_html, start_element, upward_distance, check_link_func):
    # go to the top
    element = start_element
    for i in range(upward_distance):
        element = element.parent
        if element is None:
            return ""
        # go to the bottom
        found_text = find_recursive_to_bottom(page_html, start_element, check_link_func, element)
        if len(found_text) > 0:
            return found_text
    return ""


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


def prepare_for_logging(s):
    if s is None:
        return ""
    s = s.translate(str.maketrans(
        {"\n": " ",
         "\t": " ",
         "\r": " "}))
    return s.strip()


def find_links_in_html_by_text(step_info, main_url, soup):
    logger = logging.getLogger("dlrobot_logger")
    if can_be_office_document(main_url):
        return
    base = get_base_url(main_url, soup)
    if base.startswith('/'):
        base = make_link(main_url, base)
    logger.debug("find_links_in_html_by_text url={} function={}".format(
        main_url, step_info.check_link_func.__name__))
    all_links_count = 0
    page_title = soup.title.string if soup.title is not None else ""
    page_html = str(soup)

    for l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            all_links_count += 1
            if not check_href_elementary(href):
                continue
            logger.debug("check link {}, \"{}\"".format(href, prepare_for_logging(l.text)))
            href = strip_viewer_prefix( make_link(base, href) )
            if step_info.check_link_func(TLinkInfo(page_html, l.text, main_url, href, l.name) ):
                link_info = {
                    'href': href,
                    'text': l.text.strip(" \r\n\t"),
                    'engine': 'urllib',
                    'tagname': l.name,
                }
                step_info.add_link_wrapper(main_url, link_info)
            else:
                if can_be_office_document(href):
                    try:
                        if step_info.check_link_func(TLinkInfo(page_html, page_title, main_url, href, l.name)):
                            found_text = page_title
                        else:
                            found_text = check_long_near_text(page_html, l, 3, step_info.check_link_func)
                    except SomeOtherTextException as err:
                        continue
                    if found_text is not None and len(found_text) > 0:
                        link_info = {
                            'href': href,
                            'text': found_text.strip(" \r\n\t"),
                            'engine': 'urllib',
                            'text_proxim': True,
                            'tagname': l.name,
                        }
                        step_info.add_link_wrapper(main_url, link_info)

    for l in soup.findAll('iframe'):
        href = l.attrs.get('src')
        if href is not None:
            all_links_count += 1
            if not check_href_elementary(href):
                continue

            href = make_link(base, href)
            if step_info.check_link_func( TLinkInfo(page_html, l.text, main_url, href, l.name)):
                link_info = {
                    'href': href,
                    'text': l.text.strip(" \r\n\t"),
                    'engine': 'urllib',
                    'tagname': l.name,
                }
                step_info.add_link_wrapper(main_url, link_info)


def click_selenium_if_no_href(step_info, main_url, driver_holder,  element, element_index):
    tag_name = element.tag_name
    link_text = element.text.strip('\n\r\t ')  # initialize here, can be broken after click
    href = element.get_attribute('href')
    page_html = driver_holder.the_driver.page_source
    save_url_without_click = False
    if href is not None and len(link_text) > 0:
        link_url = make_link(main_url, href) # try to get url without click a normal link
        downloaded_file = None
        save_url_without_click = True
    else:
        consider_request_policy(main_url + " elem_index=" + str(element_index), "click_selenium")
        driver_holder.click_element(element)
        link_url = driver_holder.the_driver.current_url
        downloaded_file = driver_holder.last_downloaded_file

    if step_info.check_link_func(TLinkInfo(page_html, link_text, main_url, link_url, tag_name, downloaded_file)):
        link_info = {
            'text': link_text,
            'engine': 'selenium',
            'tagname': tag_name,
        }
        if save_url_without_click:
            link_info['got_url_wo_click'] = True
        else:
            link_info['title'] = driver_holder.the_driver.title

        if driver_holder.last_downloaded_file is not None:
            link_info['downloaded_file'] = driver_holder.last_downloaded_file
            link_info['element_index'] = element_index
            step_info.add_downloaded_file_wrapper(main_url, link_info)
        else:
            link_info['href'] = link_url
            step_info.add_link_wrapper(main_url, link_info)

    driver_holder.close_window_tab()




def click_all_selenium(step_info, main_url, driver_holder):
    logger = step_info.website.logger
    logger.debug("find_links_with_selenium url={0} , function={1}".format(main_url, step_info.check_link_func.__name__))
    consider_request_policy(main_url, "GET_selenium")
    elements = driver_holder.navigate_and_get_links(main_url)
    page_html = driver_holder.the_driver.page_source
    for i in range(len(elements)):
        element = elements[i]
        link_text = element.text.strip('\n\r\t ') if element.text is not None else ""
        if len(link_text) > 0:
            logger.debug("check element {} before click, text={}".format(i, prepare_for_logging(link_text)))
            if step_info.check_link_func(TLinkInfo(page_html, link_text)):
                if element.tag_name == "a":
                    #no click needed just read href
                    href = element.get_attribute("href")
                    if step_info.check_link_func(TLinkInfo(page_html, link_text, main_url, href, element.tag_name)):
                        link_info = {
                            'text': link_text,
                            'engine': 'selenium',
                            'tagname': element.tag_name,
                            'href': href
                        }
                        step_info.add_link_wrapper(main_url, link_info)
                else:
                    click_selenium_if_no_href(step_info, main_url, driver_holder,  element, i)
                    elements = driver_holder.get_buttons_and_links()


