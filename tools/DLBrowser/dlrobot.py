import sys
import os
import json
from bs4 import BeautifulSoup
from download import download_html_with_urllib, download_with_cache, find_links_with_selenium
from urllib.parse import urlparse


def read_one_office_info (table_url):
    html = download_html_with_urllib(table_url)
    #html = open("office_page.html ", "r", encoding="utf8").read();
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

def find_links_by_text(main_url, html, check_text_func):
    soup = BeautifulSoup(html, 'html5lib')
    links = []
    for  l in soup.findAll('a'):
        if  check_text_func(l.text):
            url = l.attrs['href']
            if not url.startswith('http'):
                parsed_uri = urlparse(main_url)
                url = url.lstrip('/')
                url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri) + url
            links.append( {"url":url, "link_text": l.text} )
    return links


def check_url(main_url, url):
    if url == "":
        return False
    if url.find('redirect') != -1:
        return False
    return main_url.strip('/') != url.strip('/')


def click_links_and_get_url(url, link_text_predicate, take_first=True):
    ad = {}
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
    return ad


def find_anticorruption_div(offices):
    for office_info in offices:
        url = office_info['url']
        sys.stderr.write(url + "\n")
        ad = click_links_and_get_url (url, check_anticorr_link_text)
        office_info['anticorruption_div'] = ad

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
            sys.stderr.write("skip manual url "  + url +  "\n")
            continue
        sys.stderr.write(url + "\n")
        ad = click_links_and_get_url(url, check_law_link_text)
        office_info['law_div'] = ad

    write_offices(offices)


def check_decree_link_text(text):
    text = text.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1
    return False

def download_decrees_html(video_links):
    for office_info in offices:
        url = office_info.get('law_div', {}).get('url', '')
        if url == '':
            sys.stderr.write("skip url " + office_info['url'] +  " (no law div info) \n")
            continue
        ad = click_links_and_get_url(url, check_decree_link_text, False)
        office_info['decrees'] = ad
    write_offices(offices)



if __name__ == "__main__":
    if not os.path.exists("data"):
        os.mkdir("data")
    #find_link_with_selenium("http://svr.gov.ru", u"Противодействие")
    #exit(1);
    #download_html_selenium("http://www.mid.ru");
    #exit(1)
    #h = download_html("http://www.rkn.gov.ru")
    #print (len(h))
    #exit(1)
    offices = read_office_list()
    #find_anticorruption_div(offices)
    find_law_div(offices)
    #download_decrees_html(offices)
