import sys
import os
import time
from bs4 import BeautifulSoup

from urllib.parse import urljoin
from download import download_with_cache, OFFICE_FILE_EXTENSIONS
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

class TLinkInfo:
    def __init__(self, text, source=None, target=None, tagName=None):
        self.Source = source
        self.Target = target
        self.Text = text
        self.TagName = tagName


def check_sub_page_or_iframe(link_info):
    if not check_self_link(link_info):
        return False
    if link_info.Target is None:
        return False
    if link_info.TagName is not None and link_info.TagName.lower() == "iframe":
        return True
    return link_info.Target.startswith(link_info.Source)




def check_self_link(link_info):
    if link_info.Target != None:
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
    i = url.find('#')
    if i != -1:
        url = url[0:i]
    return url

class SomeOtherTextException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return (repr(self.value))


def find_recursive_to_bottom (element, check_link_func):
    children = element.findChildren()
    if len(children) == 0:
        if len(element.text) > 0:
            if check_link_func(TLinkInfo(element.text)):
                return element.text
            if len (element.text.strip()) > 10:
                raise SomeOtherTextException (element.text.strip())
    else:
        for child in children:
            found_text = find_recursive_to_bottom(child, check_link_func)
            if len(found_text) > 0:
                return found_text
    return ""


def go_to_the_top (element, max_iterations_count, check_link_func):
    for i  in range(max_iterations_count):
        element = element.parent
        if element is None:
            return ""
        found_text = find_recursive_to_bottom (element, check_link_func)
        if len(found_text) > 0:
            return found_text
    return ""


def is_office_document(href):
    global OFFICE_FILE_EXTENSIONS
    filename, file_extension = os.path.splitext(href)
    return file_extension.lower() in OFFICE_FILE_EXTENSIONS


def find_links_in_html_by_text(main_url, html, check_link_func):
    soup = BeautifulSoup(html, 'html5lib')
    links = {}
    base = main_url
    for l in soup.findAll('base'):
        href = l.attrs.get('href')
        if href is not None:
            base = href

    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            if href.startswith('mailto:'):
                continue

            href = make_link(base, href)

            if  check_link_func( TLinkInfo(l.text, main_url, href, l.name) ):
                links[href] = {'text': l.text, 'engine': 'urllib', 'source':  main_url}
            else:
                if is_office_document(href):
                    try:
                        found_text = go_to_the_top(l, 3, check_link_func)
                        if len(found_text) > 0:
                            links[href] = {'text': found_text, 'engine': 'urllib', 'source':  main_url}
                    except SomeOtherTextException as err:
                        continue

    for  l in soup.findAll('iframe'):
        href = l.attrs.get('src')
        if href is not None:
            if href.startswith('mailto:'):
                continue

            href = make_link(base, href)
            if  check_link_func( TLinkInfo(l.text, main_url, href, l.name) ):
                links[href] = {'text': l.text, 'engine': 'urllib', 'source':  main_url}

    return links


def find_links_with_selenium (main_url, check_link_func):
    driver = webdriver.Firefox()
    driver.implicitly_wait(5)
    driver.get(main_url)
    time.sleep(6)
    elements = list(driver.find_elements_by_xpath('//button | //a'))
    links = dict()
    for i in range(len(elements)):
        e = elements[i]
        tag_name = e.tag_name
        link_text = e.text.strip('\n\r\t ') #initialize here, can be broken after click
        if check_link_func(TLinkInfo(link_text)):
            e.click()
            time.sleep(6)
            link_url = driver.current_url
            if check_link_func(TLinkInfo(link_text, main_url, link_url, tag_name)):
                links[link_url] = {'text': link_text, 'engine': 'selenium', 'source':  main_url}
            driver.back()
            elements = list(driver.find_elements_by_xpath('//button | //a'))
    driver.quit()
    return links



def add_links(ad, url, check_link_func, fallback_to_selenium=True):
    html = ""
    try:
        html = download_with_cache(url)
    except Exception as err:
        sys.stderr.write('cannot download page url={0} while add_links, exception={1}\n'.format(url, str(err)))
        ad['exception'] = str(err)
        return

    try:
        links = find_links_in_html_by_text(url, html, check_link_func)
        if len(links) == 0 and fallback_to_selenium:
            links = find_links_with_selenium(url, check_link_func)
        if 'links' not in ad:
            ad['links'] = dict()
        ad['links'].update(links)

    except Exception as err:
        sys.stderr.write('cannot download page url={0} while find_links, exception={1}\n'.format(url, str(err)))
        ad['exception'] = str(err)



def find_links_in_page_with_urllib(url, check_link_func):
    try:
        html = download_with_cache(url)
        if html == "binary_data":
            return []
        return find_links_in_html_by_text(url, html, check_link_func)
    except Exception as err:
        sys.stderr.write('cannot download page: ' + url + "\n")
        return []


FIXLIST =  {
    "anticorruption_div": [
        ('fsin.su', "http://www.fsin.su/anticorrup2014/"),
        ('fso.gov.ru',  "http://www.fso.gov.ru/korrup.html")
    ]
}


def find_links_for_one_website(start_pages, target, check_link_func, fallback_to_selenium=False, transitive=False):

    while True:
        save_count = len(target['links'])

        for url in start_pages:
            sys.stderr.write("process " + url + "\n")
            add_links(target, url, check_link_func, fallback_to_selenium)

        new_count = len(target['links'])
        if not transitive or save_count == new_count:
            break


def find_links_for_all_websites(offices, source_page_collection_name, target_page_collection_name,
                                check_link_func, fallback_to_selenium=True, transitive=False, only_missing=True,
                                include_source="copy_if_empty"):
    for office_info in offices:
        name = office_info['name']
        if target_page_collection_name not in office_info:
            office_info[target_page_collection_name] = dict()
        target = office_info[target_page_collection_name]
        if 'links' not in target:
            target['links'] = dict()

        if target.get('engine', '') == 'manual':
            sys.stderr.write("skip manual url updating {0}, target={1}\n".format(
                name, target_page_collection_name))
            continue
        if len(target['links']) > 0 and only_missing:
            sys.stderr.write("skip manual url updating {0}, target={1}, (already exist)\n".format(
                name, target_page_collection_name))
            continue

        start_pages = office_info.get(source_page_collection_name, {}).get('links', dict())

        if include_source == "always":
            target['links'].update(start_pages)

        find_links_for_one_website(start_pages, target,
                                   check_link_func, fallback_to_selenium, transitive)

        if include_source == "copy_if_empty" and len(target['links']) == 0:
            target['links'].update(start_pages)

        if len(target) == 0 and len(start_pages) > 0:
            for (s,t) in FIXLIST.get(target_page_collection_name, []):
                if start_pages[0].find(s) != -1:
                    target[t] = [{"text":  "", "engine": "manual"}]


def collect_subpages(offices, source_page_collection_name, target_page_collection_name, check_link_func,
                     include_source="always"):
    find_links_for_all_websites(offices, source_page_collection_name, target_page_collection_name,
                                check_link_func,
                                fallback_to_selenium=False,
                                transitive=True,
                                only_missing=False,
                                include_source=include_source)
