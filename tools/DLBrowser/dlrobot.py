import sys
import os
import re
import json
from bs4 import BeautifulSoup
from download import download_html_with_urllib, \
    download_with_cache, \
    find_links_with_selenium, \
    FILE_CACHE_FOLDER, \
    build_temp_local_file
from urllib.parse import urljoin


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

#попробовать автоматизировать консультант плюс !!!

def check_url(main_url, url):
    if url == "":
        return False
    if url.find('redirect') != -1:
        return False
    return main_url.strip('/') != url.strip('/')


def click_first_link_and_get_url(office_info, div_name, url, link_text_predicate):
    ad = {}
    old_ad = office_info.get(div_name, {})
    if 'comment' in old_ad:
        ad['comment'] = old_ad['comment']

    try:
        html = download_with_cache(url)
        links = find_links_by_text(url, html, link_text_predicate)
        engine = ""
        if len(links) > 0 and check_url(url, links[0].link_url):
            engine = "urllib"
        elif use_selenium:
            links = find_links_with_selenium(url, link_text_predicate)
            if len(links) > 0 and check_url(url, links[0].link_url):
                engine = "selenium"
            else:
                ad['exception'] = "no link found"

        if engine != "":
            if take_first:
                ad['url'] = links[0].link_url
                ad['link_text'] = links[0].link_text
                ad['engine'] = engine
            else:
                ad['engine'] = engine
                ad['links'] = [ l.to_json() for l in links ]

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


def check_anticorr_link_text(href, text):
    text = text.strip().lower()
    if text.startswith(u'противодействие'):
        return text.find("коррупц") != -1
    return False

def find_anticorruption_div(offices):
    for office_info in offices:
        url = office_info['url']
        sys.stderr.write(url + "\n")
        click_first_link_and_get_url(office_info, 'anticorruption_div', url,  check_anticorr_link_text)

    write_offices(offices)


def check_law_link_text(href, text):
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
        click_first_link_and_get_url(office_info, 'law_div', url, check_law_link_text)

    write_offices(offices)



def check_office_decree_link_text(href, text):
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
        click_first_link_and_get_url(office_info, 'office_decrees', url, check_office_decree_link_text)

    write_offices(offices)


def get_decree_pages(offices):
    for office_info in offices:
        law_div = office_info.get('law_div', {})
        main_link = TLink(json_dict=law_div)
        if main_link.link_url == '':
            sys.stderr.write("skip url " + office_info['url'] +  " (no law div info) \n")
            continue
        office_link = TLink(json_dict=office_info.get('office_decrees', {}))
        if office_link.link_url != "":
            main_link = office_link
        all_links = set([main_link])
        processed_links = set()
        left_urls = all_links
        while len(left_urls) > 0:
            link = list(left_urls)[0]
            sys.stderr.write(link.link_url + "\n")
            try:
                html = download_with_cache(link.link_url)
                links = find_links_to_subpages(link.link_url, html)
                all_links = all_links.union(links)
            except  Exception as err:
                sys.stderr.write("cannot process " + link.link_url + ": " + str(err) + "\n")
                pass
            processed_links.add(link)
            left_urls = all_links.difference(processed_links)
        office_info['decree_pages'] = list( l.to_json() for l in all_links)

    write_offices(offices)

def check_download_text(href, text):
    if text.startswith(u'кодекс'):
        return True
    if text.startswith(u'скачать'):
        return True
    if text.startswith(u'загрузить'):
        return True
    if text.startswith(u'docx'):
        return True
    if text.startswith(u'doc'):
        return True
    if text.find('.doc') != -1 or text.find('.docx') != -1 or text.find('.pdf') != -1 or  text.find('.rtf') != -1:
        return True
    return False

def check_decree_link_text(href, text):
    text = text.strip(' \n\t\r').lower()
    if text.startswith(u'приказ'):
        return True
    if text.startswith(u'распоряжение'):
        return True
    if check_download_text(href, text):
        return True
    return False


def find_decrees_doc_urls(offices):
    for office_info in offices:
        docs = set()
        for link_json in office_info.get('decree_pages', []):
            link = TLink(json_dict=link_json)
            sys.stderr.write(link.link_url + "\n")
            new_docs = find_links_in_page_with_urllib(link, check_decree_link_text)
            docs = docs.union(new_docs)

        additional_docs = set()
        for link in docs:
            sys.stderr.write("download " +  link.link_url + "\n")
            try:
                new_docs =  find_links_in_page_with_urllib(link, check_download_text)
                additional_docs = additional_docs.union(new_docs)
            except  Exception as err:
                sys.stderr.write("cannot download " + link.link_url + ": " + str(err) + "\n")
                pass

        for link in additional_docs:
            sys.stderr.write("download additional " + link.link_url + "\n")
            try:
                download_with_cache(link.link_url)
            except  Exception as err:
                sys.stderr.write("cannot download " + link.link_url + ": " + str(err) + "\n")
                pass

        docs = docs.union(additional_docs)
        office_info['anticor_doc_urls'] = [x.to_json() for x in docs]
    write_offices(offices)


def convert_to_text(offices):
    for office_info in offices:
        txtfiles = []
        for d in office_info.get('anticor_doc_urls', []):
            link = TLink(json_dict= d)

            try:
                file_name = build_temp_local_file(link.link_url)
                if file_name == "":
                    continue
                txt_file = file_name + ".txt"
                if not os.path.exists(txt_file) or os.path.getsize(txt_file) == 0:
                    cmd = "..\\DocConvertor\\DocConvertor\\DocConvertor\\bin\\Debug\\DocConvertor.exe {} > {}".format(
                        file_name, txt_file
                    )
                    sys.stderr.write(cmd + "\n")
                    os.system (cmd)
                if os.path.exists(txt_file) and os.path.getsize(txt_file) > 0:
                    txtfiles.append(txt_file)
            except Exception as err:
                sys.stderr.write(str(err) + "\n")

        office_info['txt_files'] = txtfiles
    write_offices(offices)


def check_decree_content(text):
    if text.find("К сожалению") != -1 or text.find("технические работы") != -1 or text.find(
            "ведутся работы по наполнению") != -1:
        return False
    return True

def cut_content(text):
    starter_found = False
    prikaz_found = False
    good_lines = []
    for line in text.split("\n"):
        if len(line) < 100:
            continue
        if not prikaz_found:
            if text.find(u"приказываю") != -1 or text.find(u"п р и к а з ы в а ю:") != -1 :
                starter_found = True
                good_lines = []
                prikaz_found = True
        if len(text) > 250:
            starter_found = True
        if starter_found:
            good_lines.append (line)
    text = " ".join(good_lines)
    return re.sub('\s+', ' ',text)


def delete_common_prefix(texts):
    if len(texts) == 0:
        return
    commonPrefix = ""
    for i in range(1, len(texts[0]['text'])):
        prefix = texts[0]['text'][0:i]
        if not prefix.endswith(' '):
            continue
        hasPrefixCount = 0
        for k in texts:
            if k['text'].startswith(prefix):
                hasPrefixCount += 1
        if hasPrefixCount !=  len(texts):
            break
        else:
            commonPrefix = prefix

    if  len(commonPrefix) > 0:
        for k in texts:
            if k['text'].startswith(commonPrefix):
                k['text'] = k['text'][len(commonPrefix):]
    return

def get_decree_id(text):
    obj = re.search(u'(?:(?:от)|(?:ОТ))\s+([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9])\s*[N№]\s*([0-9]+)', text, re.UNICODE)
    if obj:
        return obj.group(1) + " N " + obj.group(2)

    #«20» __04______2015 г.                                                                                                               № 1 / 2999
    obj = re.search(u'([0-9][0-9]?[»«\s_]+[а-я]+[\s_]+[0-9][0-9][0-9][0-9])[\s_]+(?:г.)?[_\s]*[N№]\s+([0-9 /]+)', text, re.UNICODE)
    if obj:
        return obj.group(1) + " N " + obj.group(2)
    return ""


def create_text_corpus(offices, corpus_file_name):
    corpus = []
    for office_info in offices:
        filtered_texts = []
        text_size = 0
        uses_ids = set()
        for txt_file in office_info.get('txt_files', []):
            if not os.path.exists(txt_file) or os.path.getsize(txt_file) == 0:
                continue
            text = ""
            with open (txt_file, "r", encoding="utf8") as inpf:
                text = inpf.read()
            decree_id = get_decree_id(text)
            if decree_id in uses_ids:
                continue
            if decree_id != "":
                uses_ids.add(decree_id)
            if check_decree_content(text):
                text = cut_content(text)
                text_size += len(text)
                if len (text) > 0:
                    filtered_texts.append ({ 'file': txt_file,
                                         'decree_id' : decree_id,
                                 'text': text})
        delete_common_prefix(filtered_texts)
        corpus.append ({
            'office_name': office_info['name'],
            'texts_size': text_size,
            'filtered_texts': filtered_texts
        })

    with open(corpus_file_name, "w", encoding="utf8") as outf:
        outf.write(json.dumps(corpus, indent=4, ensure_ascii=False))


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
    #get_decree_pages(offices)
    #find_decrees_doc_urls(offices)
    #find_decrees_doc_urls(offices)
    #convert_to_text(offices)
    s = u"от 25.01.2019 №799"
    get_decree_id(s)
    create_text_corpus(offices, "decree_corpus.txt")