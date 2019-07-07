import sys
import os
import json
from bs4 import BeautifulSoup
from download import download_html_with_urllib, download_with_cache, find_links_with_selenium, FILE_CACHE_FOLDER
from urllib.parse import urljoin

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
        if  check_text_func(l.text):
            href = l.attrs.get('href')
            if href is not None:
                url = make_link(main_url, href)
                links.append( {"url":url, "link_text": l.text.strip(' \r\n\t')} )
    return links


def find_links_to_subpages(main_url, html):
    soup = BeautifulSoup(html, 'html5lib')
    links = set()
    for  l in soup.findAll('a'):
        href = l.attrs.get('href')
        if href is not None:
            url = make_link(main_url, href)
            if url.startswith(main_url):
                links.add( url )

    return links

#попробовать автоматизировать консультант плюс !!!

def check_url(main_url, url):
    if url == "":
        return False
    if url.find('redirect') != -1:
        return False
    return main_url.strip('/') != url.strip('/')


def click_links_and_get_url(office_info, div_name, url, link_text_predicate, take_first=True):
    ad = {}
    old_ad = office_info.get(div_name, {})
    if 'comment' in old_ad:
        ad['comment'] = old_ad['comment']

    try:
        html = download_with_cache(url)
        links = find_links_by_text(url, html, link_text_predicate)
        engine = ""
        if len(links) > 0 and check_url(url, links[0]["url"]):
            engine = "urllib"
        else:
            links = find_links_with_selenium(url, link_text_predicate)
            if len(links) > 0 and check_url(url, links[0]["url"]):
                engine = "selenium"
            else:
                ad['exception'] = "no link found"

        if engine != "":
            if take_first:
                ad['url'] = links[0]["url"]
                ad['link_text'] = links[0]["link_text"]
                ad['engine'] = engine
            else:
                ad['engine'] = engine
                ad['links'] = links

    except Exception as err:
        sys.stderr.write('cannot download page: ' + url + "\n")
        ad['exception'] = str(err)

    office_info[div_name] = ad


def read_one_office_info (table_url):
    html = download_html_with_urllib(table_url)
    soup = BeautifulSoup(html, 'html5lib')
    office_info = {};
    for text in soup.findAll('div', {"class": "text"}):
        for table in text.findChildren('table', recursive=True):
            for row in table.findChildren('tr'):
                if row.text.find('Web-адрес') != -1:
                    cells = list(row.findAll('td'))
                    office_info['url'] = cells[1].text
    return office_info


def write_offices(offices):
    with open("offices.txt", "w", encoding="utf8") as outf:
        outf.write(json.dumps(offices, ensure_ascii=False,indent=4))

def read_office_list():
    with open("offices.txt", "r", encoding="utf8") as inpf:
        return json.loads(inpf.read())


def create_office_list():
    html = download_html_with_urllib("https://www.consultant.ru/document/cons_doc_LAW_65443/")
    soup = BeautifulSoup(html, 'html5lib')
    offices = []
    for  l in soup.findAll('a'):
        words = l.text.split()
        if len(words) == 0:
            continue
        first_word = words[0]
        if first_word not in {u"Министерство", u"Федеральное", u"Федеральная", u"Главное", u"Управление", u"Государственная", u"Служба"}:
            continue
        url = l.attrs['href']
        if not url.startswith('http://www.consultant.ru'):
            url = 'http://www.consultant.ru' + url
        office_info = read_one_office_info(url)
        office_info['name'] = l.text.strip('\n ')
        offices.append(office_info)
    write_offices(offices)
    return offices


def check_anticorr_link_text(text):
    text = text.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1
    return False

def find_anticorruption_div(offices):
    for office_info in offices:
        url = office_info['url']
        sys.stderr.write(url + "\n")
        click_links_and_get_url (office_info, 'anticorruption_div', url,  check_anticorr_link_text)

    write_offices(offices)


def check_law_link_text(text):
    text = text.strip().lower()
    if text.find("коррупц") == -1:
        return False
    if text.startswith(u'нормативные'):
        return True;
    if text.startswith(u'нормативно'):
        return True;
    if text.startswith(u'нпа'):
        return True;
    return False


def find_law_div(offices):
    for office_info in offices:
        url = office_info.get('anticorruption_div', {}).get('url', '')
        if url == '':
            sys.stderr.write("skip url "  + office_info['url'] +  " (no div info) \n")
            continue
        if office_info.get('law_div',  {}).get('engine',  '') == 'manual':
            sys.stderr.write("skip manual url updating "  + url +  "\n")
            continue
        sys.stderr.write(url + "\n")
        click_links_and_get_url(office_info, 'law_div', url, check_law_link_text)

    write_offices(offices)



def check_office_decree_link_text(text):
    text = text.strip(' \n\t\r').lower()
    if text.startswith(u'ведомственные'):
        return True
    if text.startswith(u'иные'):
        return True
    return False


def find_office_decrees_section(offices):
    for office_info in offices:
        url = office_info.get('law_div', {}).get('url', '')
        if url == '':
            sys.stderr.write("skip url " + office_info['url'] + " (no law div info)\n")
            continue
        sys.stderr.write(url + "\n")
        click_links_and_get_url(office_info, 'office_decrees', url, check_office_decree_link_text, True)

    write_offices(offices)

def get_decree_pages(offices):
    for office_info in offices:
        url = office_info.get('law_div', {}).get('url', '')
        if url == '':
            sys.stderr.write("skip url " + office_info['url'] +  " (no law div info) \n")
            continue
        office_url = office_info.get('office_decrees', {}).get('url', '')
        if office_url != "":
            url = office_url
        all_links = set([url])
        processed_links = set()
        left_urls = all_links
        while len(left_urls) > 0:
            url = list(left_urls)[0]
            sys.stderr.write(url + "\n")
            try:
                html = download_with_cache(url)
                links = find_links_to_subpages(url, html)
                all_links = all_links.union(links)
            except  Exception as err:
                sys.stderr.write("cannot process " + url + ": " + str(err) + "\n")
                pass
            processed_links.add(url)
            left_urls = all_links.difference(processed_links)
        office_info['decree_pages'] = list(all_links)

    write_offices(offices)

def check_decree_link_text(text):
    text = text.strip(' \n\t\r').lower()
    if text.startswith(u'приказ'):
        return True
    return False


def download_decrees_html(offices):
    for office_info in offices:
        url = office_info.get('law_div', {}).get('url', '')
        if url == '':
            sys.stderr.write("skip url " + office_info['url'] +  " (no law div info) \n")
            continue
        office_url = office_info.get('office_decrees', {}).get('url', '')
        if office_url != "":
            url = office_url
        sys.stderr.write(url + "\n")

        click_links_and_get_url(office_info, 'office_decrees', url, check_decree_link_text, False)

    write_offices(offices)


if __name__ == "__main__":
    global FILE_CACHE_FOLDER

    #url = 'http://www.mnr.gov.ru/open_ministry/anticorruption/npa_v_sfere_protivodeystviya_korruptsii/'
    #html = download_with_cache(url)
    #links = find_links_to_subpages(url, html)
    #exit(1)
    
    if not os.path.exists(FILE_CACHE_FOLDER):
        os.mkdir(FILE_CACHE_FOLDER)
    # offices = create_office_list():
    offices = read_office_list()
    #find_anticorruption_div(offices)
    #find_law_div(offices)
    #find_office_decrees_section(offices)
    #find_office_decrees_section(offices)
    get_decree_pages(offices)
    # download_decrees_html(offices)
