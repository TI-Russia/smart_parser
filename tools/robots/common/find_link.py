import sys
import os
from bs4 import BeautifulSoup

from urllib.parse import urljoin
from download import download_with_cache, OFFICE_FILE_EXTENSIONS
from selenium import webdriver


class TLinkInfo:
    def __init__(self, text, source=None, target=None):
        self.Source = source
        self.Target = target
        self.Text = text


def check_sub_page(link_info):
    if not check_self_link(link_info):
        return False
    if link_info.Target is None:
        return False
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
    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            href = make_link(main_url, href)
            if  check_link_func( TLinkInfo(l.text, main_url, href) ):
                links[href] = { 'text': l.text, 'engine': 'urllib', 'source':  main_url}
            else:
                if is_office_document(href):
                    try:
                        found_text = go_to_the_top(l, 3, check_link_func)
                        if len(found_text) > 0:
                            links[href] = {'text': found_text, 'engine': 'urllib', 'source':  main_url}
                    except SomeOtherTextException as err:
                        continue

    return links


def find_links_with_selenium (url, check_link_func):
    browser = webdriver.Firefox()
    browser.implicitly_wait(5)
    browser.get(url)
    time.sleep(6)
    elements = browser.find_elements_by_xpath('//button | //a')
    links = dict()
    for e in elements:
        if check_link_func(TLinkInfo(e.text)):
            e.click()
            time.sleep(6)
            browser.switch_to.window(browser.window_handles[-1])
            link_url = browser.current_url
            if check_link_func(TLinkInfo(e.text, url, link_url)):
                links[link_url] = {'text': e.text.strip('\n\r\t '), 'engine': 'selenium', 'source':  main_url}
            browser.switch_to.window(browser.window_handles[0])
    browser.quit()
    return links



def add_links(ad, url, check_link_func, use_selenium=True):
    try:
        html = download_with_cache(url)
        links = find_links_in_html_by_text(url, html, check_link_func)
        if len(links) == 0 and use_selenium:
            links = find_links_with_selenium(url, check_link_func)
        if 'links' not in ad:
            ad['links'] = dict()
        ad['links'].update(links)

    except Exception as err:
        sys.stderr.write('cannot download page: ' + url + "\n")
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

def find_links(office_info, source_page_collection_name, target_page_collection_name, check_link_func, use_selenium, only_missing):
    if target_page_collection_name not in office_info:
        office_info[target_page_collection_name] = dict()

    target_collection = office_info[target_page_collection_name]
    name = office_info['name']

    if target_collection.get('engine', '') == 'manual':
        sys.stderr.write("skip manual url updating " + name + "\n")
        return

    if len(target_collection.get('links', dict())) > 0 and only_missing:
        sys.stderr.write("skip updating for " + name + " (already exist) \n")
        return
    
    start_pages = office_info.get(source_page_collection_name, {}).get('links', {})

    for url in start_pages:
        sys.stderr.write("process " + url + "\n")
        add_links(target_collection, url, check_link_func, use_selenium)

    if len(target_collection.get('links', dict())) == 0 and len(start_pages) > 0:
        for (s,t) in FIXLIST.get(target_page_collection_name, []):
            if start_pages[0].find(s) != -1:
                target_collection['links'][t] = [{"text":"", "engine":"manual"}]

    if len(target_collection.get('links', dict())) == 0:
        target_collection['links'] = dict(start_pages)


    # manual fix list (sometimes they use images instead of text...)
    if url.find('fsin.su') != -1:
        office_info["anticorruption_div"] = [{
            "url": "http://www.fsin.su/anticorrup2014/",
            "engine": "manual"
        }]

    if url.find('fso.gov.ru') != -1:
        office_info["anticorruption_div"] = [{
            "url": "http://www.fso.gov.ru/korrup.html",
            "engine": "manual"
        }]


def get_links_count (office_info, page_collection_name):
    return len(office_info.get(page_collection_name, {}).get('links', dict()))


def find_links_for_all_websites(offices, source_page_collection_name, target_page_collection_name,
                                check_link_func, use_selenium=False, transitive=False, only_missing=True):
    for office_info in offices:
        while True:
            save_count = get_links_count(office_info, target_page_collection_name)
            find_links(office_info, source_page_collection_name, target_page_collection_name, check_link_func, use_selenium, only_missing)
            new_count =  get_links_count(office_info, target_page_collection_name)
            if not transitive or save_count == new_count:
                break



def collect_subpages(offices, source_page_collection_name, target_page_collection_name):
    find_links_for_all_websites(offices, source_page_collection_name, target_page_collection_name,
                                check_sub_page, False, True, False)
