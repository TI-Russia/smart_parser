import sys
import os
import json
sys.path.append('../common')

from download import download_html_with_urllib, \
    download_with_cache, \
    find_links_with_selenium, \
    FILE_CACHE_FOLDER, \
    build_temp_local_file

from office_list import  create_office_list, read_office_list, write_offices
from find_link import click_first_link_and_get_url, \
    find_links_to_subpages, \
    find_links_in_page_with_urllib

from main_anticor_div import find_anticorruption_div



def declarations_link_text(href, text):
    text = text.strip().strip('"').lower()
    text = " ".join(text.split())
    if text.startswith(u'сведения о доходах'):
        return True
    if text.startswith(u'cведения о доходах'): # transliteration
        return True


    if text.find("коррупц") == -1:
        return False
    if text.startswith(u'сведения'):
        return True;
    return False


def find_declarations_div(offices, only_missing=False):
    for office_info in offices:
        existing_link = office_info.get('declarations_div', {})
        if existing_link.get('engine', '') == 'manual':
            sys.stderr.write("skip manual url updating " + url + "\n")
            continue
        if existing_link.get('url') != None and only_missing:
            continue

        anticor_div_url = office_info.get('anticorruption_div', {}).get('url', '')
        if anticor_div_url == '':
            # cannot find  declarations_div (see svr.gov.ru)
            sys.stderr.write("try to get division from the morda "  + office_info['url'] +  " (no anticor_div_url) \n")
            click_first_link_and_get_url(office_info, 'declarations_div', office_info['url'], declarations_link_text)
        else:
            sys.stderr.write(anticor_div_url + "\n")
            click_first_link_and_get_url(office_info, 'declarations_div', anticor_div_url, declarations_link_text)



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



if __name__ == "__main__":
    global FILE_CACHE_FOLDER

    if not os.path.exists(FILE_CACHE_FOLDER):
        os.mkdir(FILE_CACHE_FOLDER)
    #offices = create_office_list()
    offices = read_office_list()
    #find_anticorruption_div(offices)
    find_declarations_div(offices, True)

    #find_office_decrees_section(offices)
    #get_decree_pages(offices)
    #find_decrees_doc_urls(offices)
    #find_decrees_doc_urls(offices)
