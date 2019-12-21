import sys
import os
from bs4 import BeautifulSoup

from urllib.parse import urljoin
from download import download_html_with_urllib, \
    download_with_cache, \
    find_links_with_selenium


class TLink:
    def __init__(self, url='', link_text='', json_dict=None):
        if json_dict is not None:
            self.from_json(json_dict)
        else:
            self.link_url = url
            self.link_text = link_text.strip(' \r\n\t')

    def __hash__(self):
        return self.link_url.__hash__()

    def __eq__(self, other):
        return self.link_url == other.link_url

    def to_json(self):
        return {'url': self.link_url, 'link_text': self.link_text }

    def from_json(self, js):
        self.link_url = js.get('url', '')
        self.link_text = js.get('link_text', '')


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

def find_recursive_to_bottom (element, check_text_func):
    children = element.findChildren()
    if len(children) == 0:
                if len(element.text) > 0:
                    if check_text_func(element.text):
                        return element.text
                    if len (element.text.strip()) > 10:
                        raise SomeOtherTextException (element.text.strip())
    else:
        for child in children:
            found_text = find_recursive_to_bottom(child, check_text_func)
            if len(found_text) > 0:
                return found_text
    return ""

def go_to_the_top (element, max_iterations_count, check_text_func):
    for i  in range(max_iterations_count):
        element = element.parent
        if element is None:
            return ""
        found_text = find_recursive_to_bottom (element, check_text_func)
        if len(found_text) > 0:
            return found_text
    return ""

def is_office_document(href):
    filename, file_extension = os.path.splitext(href)
    return file_extension.lower() in {'.doc', '.pdf', '.docx', '.xls', '.xlsx', '.rtf'}


def find_links_by_text(main_url, html, check_text_func):
    soup = BeautifulSoup(html, 'html5lib')
    links = []
    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            if  check_text_func(l.text):
                url = make_link(main_url, href)
                links.append(TLink(url, l.text))
            else:
                if is_office_document(href):
                    try:
                        found_text = go_to_the_top(l, 3, check_text_func)
                        if len(found_text) > 0:
                            url = make_link(main_url, href)
                            links.append(TLink(url, found_text))
                    except SomeOtherTextException as err:
                        continue

    return links



def check_url(main_url, url):
    if url == "":
        return False
    if url.find('redirect') != -1:
        return False
    return main_url.strip('/') != url.strip('/')


def click_first_link_and_get_url(office_info, div_name, url, link_text_predicate, use_selenium=False):
    ad = {}
    old_ad = office_info.get(div_name, {})
    if 'comment' in old_ad:
        ad['comment'] = old_ad['comment']

    try:
        html = download_with_cache(url, use_selenium)
        engine = "urllib"
        links = find_links_by_text(url, html, link_text_predicate)
        good_links  = [link for link in links  if check_url(url, link.link_url)]
        if  len(good_links) == 0:
            links = find_links_with_selenium(url, link_text_predicate)
            engine = "selenium"
            good_links = [link for link in links if check_url(url, link.link_url)]
        if  len(good_links) > 0:
            ad['url'] = good_links[0].link_url
            ad['link_text'] = good_links[0].link_text
            ad['engine'] = engine
        else:
            ad['exception'] = "no link found"


    except Exception as err:
        sys.stderr.write('cannot download page: ' + url + "\n")
        ad['exception'] = str(err)

    office_info[div_name] = ad


def find_links_in_page_with_urllib(link, link_text_predicate):
    try:
        html = download_with_cache(link.link_url)
        if html == "binary_data":
            return []
        return find_links_by_text(link.link_url, html, link_text_predicate)
    except Exception as err:
        sys.stderr.write('cannot download page: ' + link.link_url + "\n")
        return []


def find_links_to_subpages(main_url, html):
    soup = BeautifulSoup(html, 'html5lib')
    links = set()
    for l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            url = make_link(main_url, href)
            if url.startswith(main_url):
                links.add( url )

    return links


def collect_all_subpages_urls(url):
    all_links = set([url])
    processed_links = set()
    left_urls = all_links
    while len(left_urls) > 0:
        link = list(left_urls)[0]
        if not is_office_document(link):
            sys.stderr.write(link + "\n")
            try:
                html = download_with_cache(link)
                links = find_links_to_subpages(link, html)
                all_links = all_links.union(links)
            except Exception as err:
                sys.stderr.write("cannot process " + link + ": " + str(err) + "\n")
                pass
        processed_links.add(link)
        left_urls = all_links.difference(processed_links)
    return all_links
