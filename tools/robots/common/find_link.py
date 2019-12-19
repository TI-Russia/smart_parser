import sys
from bs4 import BeautifulSoup

from urllib.parse import urljoin
from download import download_html_with_urllib, \
    download_with_cache


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


def find_links_by_text(main_url, html, check_text_func):
    soup = BeautifulSoup(html, 'html5lib')
    links = []
    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            if  check_text_func(href, l.text):
                url = make_link(main_url, href)
                links.append(TLink(url, l.text))
    return links


def find_links_to_subpages(main_url, html):
    soup = BeautifulSoup(html, 'html5lib')
    links = set()
    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            url = make_link(main_url, href)
            if url.startswith(main_url):
                links.add( TLink(url, l.text ) )

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
