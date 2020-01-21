import os
from pathlib import Path
import time
import logging
import shutil
from urllib.parse import urljoin, unquote
from download import download_with_cache, ACCEPTED_DECLARATION_FILE_EXTENSIONS, \
    save_download_file, DEFAULT_HTML_EXTENSION, get_file_extension_by_cached_url, get_site_domain_wo_www

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class TLinkInfo:
    def __init__(self, text, source=None, target=None, tagName=None, download_file=None):
        self.Source = source
        self.Target = target
        self.Text = text
        self.TagName = tagName
        self.DownloadFile = download_file


def strip_viewer_prefix(href):
    # https://docs.google.com/viewer?url=https%3A%2F%2Foren-rshn.ru%2Findex.php%3Fdo%3Ddownload%26id%3D247%26area%3Dstatic%26viewonline%3D1
    viewers = ['https://docs.google.com/viewer?url=',
                'https://docviewer.yandex.ru/?url=',
                'https://view.officeapps.live.com/op/embed.aspx?src=',
                'https://view.officeapps.live.com/op/view.aspx?src=']
    for prefix in viewers:
        if href.startswith(prefix):
            href = href[len(prefix):]
            return unquote(href)
    return href


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
    if not check_self_link(link_info):
        return False
    if link_info.Target is None:
        return False
    if link_info.TagName is not None and link_info.TagName.lower() == "iframe":
        return True
    parent = strip_html_url(link_info.Source)
    subpage = strip_html_url(link_info.Target)
    return subpage.startswith(parent)


def check_self_link(link_info):
    if link_info.Target is not None:
        if len(link_info.Target) == 0:
            return False
        if link_info.Target.find('redirect') != -1:
            return False
        if link_info.Source.strip('/') == link_info.Target.strip('/'):
            return False
    return True


def check_anticorr_link_text(link_info):
    if not check_self_link(link_info):
        return False

    text = link_info.Text.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1

    return False


def make_link(main_url, href):
    url = urljoin(main_url, href)
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


def find_recursive_to_bottom (start_element, check_link_func, element):
    children = element.findChildren()
    if len(children) == 0:
        if len(element.text) > 0 and element != start_element:
            if check_link_func(TLinkInfo(element.text)):
                return element.text
            if len (element.text.strip()) > 10:
                raise SomeOtherTextException (element.text.strip())
    else:
        for child in children:
            found_text = find_recursive_to_bottom(start_element, check_link_func, child)
            if len(found_text) > 0:
                return found_text
    return ""


def check_long_near_text (start_element, upward_distance, check_link_func):
    # go to the top
    element = start_element
    for i in range(upward_distance):
        element = element.parent
        if element is None:
            return ""
        # go to the bottom
        found_text = find_recursive_to_bottom (start_element, check_link_func, element)
        if len(found_text) > 0:
            return found_text
    return ""


def can_be_office_document(href):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    filename, file_extension = os.path.splitext(href)
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


def check_http(href):
    if href.startswith('mailto:'):
        return False
    if href.startswith('tel:'):
        return False
    if href.startswith('javascript:'):
        return False
    return True


def find_links_in_html_by_text(step_info, main_url, soup):
    logger = logging.getLogger("dlrobot_logger")
    if can_be_office_document(main_url):
        return
    base = get_base_url(main_url, soup)
    logger.debug("find_links_in_html_by_text function={0}".format(step_info.check_link_func))
    all_links_count = 0
    for l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            all_links_count += 1
            if not check_http(href):
                continue
            logger.debug("check link {0}".format(href))
            href = strip_viewer_prefix( make_link(base, href) )
            if  step_info.check_link_func( TLinkInfo(l.text, main_url, href, l.name) ):
                link_info = {
                    'href': href,
                    'text': l.text,
                    'engine': 'urllib',
                    'tagname': l.name,
                }
                step_info.add_link_wrapper(main_url, link_info)
            else:
                if can_be_office_document(href):
                    try:
                        if step_info.check_link_func(TLinkInfo(soup.title.string, main_url, href, l.name)):
                            found_text = soup.title.string
                        else:
                            found_text = check_long_near_text(l, 3, step_info.check_link_func)
                    except SomeOtherTextException as err:
                        continue
                    if len(found_text) > 0:
                        link_info = {
                            'href': href,
                            'text': found_text,
                            'engine': 'urllib',
                            'text_proxim': True,
                            'tagname': l.name,
                        }
                        step_info.add_link_wrapper(main_url, link_info)

    for l in soup.findAll('iframe'):
        href = l.attrs.get('src')
        if href is not None:
            all_links_count += 1
            if not check_http(href):
                continue

            href = make_link(base, href)
            if step_info.check_link_func( TLinkInfo(l.text, main_url, href, l.name)):
                link_info = {
                    'href': href,
                    'text': l.text,
                    'engine': 'urllib',
                    'tagname': l.name,
                }
                step_info.add_link_wrapper(main_url, link_info)


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


def wait_download_finished(tmp_folder, timeout=120):
    dl_wait = True
    seconds = 0
    while dl_wait and seconds < timeout:
        firefox_temp_file = sorted(Path(tmp_folder).glob('*.part'))
        chrome_temp_file = sorted(Path(tmp_folder).glob('*.crdownload'))
        if (len(firefox_temp_file) == 0) and \
           (len(chrome_temp_file) == 0):
            files = os.listdir(tmp_folder)
            if len(files) > 0:
                return save_download_file(os.path.join(tmp_folder, files[0]))
            return None
        time.sleep(1)
        seconds += 1
    return None


def click_selenium(step_info, main_url, driver, download_folder, element, element_index):
    tag_name = element.tag_name
    link_text = element.text.strip('\n\r\t ')  # initialize here, can be broken after click
    make_folder_empty(download_folder)
    window_before = driver.window_handles[0]
    #element.click()

    # open in a new tab, send ctrl-click
    ActionChains(driver) \
        .key_down(Keys.CONTROL) \
        .click(element) \
        .key_up(Keys.CONTROL) \
        .perform()

    time.sleep(6)
    if len(driver.window_handles) < 2:
        step_info.website.logger.debug("cannot click, no new window is found")
        return
    window_after = driver.window_handles[1]
    driver.switch_to_window(window_after)
    downloaded_file = wait_download_finished(download_folder, 180)
    link_url = driver.current_url
    if step_info.check_link_func(TLinkInfo(link_text, main_url, link_url, tag_name, downloaded_file)):
        link_info = {
            'text': link_text,
            'engine': 'selenium',
            'tagname': tag_name,
            'title': driver.title
        }
        if downloaded_file is not None:
            link_info['downloaded_file'] = downloaded_file
            link_info['element_index'] = element_index
            step_info.add_downloaded_file_wrapper(main_url, link_info)
        else:
            link_info['href'] = link_url
            step_info.add_link_wrapper(main_url, link_info)
    driver.close()
    driver.switch_to_window(window_before)


def close_all_windows_except_one(driver):
    while len(driver.window_handles) > 1:
        driver.close()


def click_all_selenium (step_info, main_url, driver, download_folder):
    logger = step_info.website.logger
    logger.debug("find_links_with_selenium url={0}, function={1}".format(main_url, step_info.check_link_func))
    close_all_windows_except_one(driver)
    driver.get(main_url)
    time.sleep(6)
    elements = list(driver.find_elements_by_xpath('//button | //a'))

    for i in range(len(elements)):
        e = elements[i]
        link_text = e.text.strip('\n\r\t ')
        logger.debug("check link url={0}, function={1}".format(main_url, step_info.check_link_func))
        if step_info.check_link_func(TLinkInfo(link_text)):
            click_selenium(step_info, main_url, driver, download_folder,  e, i)
            elements = list(driver.find_elements_by_xpath('//button | //a'))


