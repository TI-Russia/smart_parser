import sys
import os
import json
sys.path.append('../common')

from download import  download_with_cache, \
    FILE_CACHE_FOLDER

from office_list import  create_office_list, read_office_list, write_offices
from find_link import get_links, \
    OFFICE_FILE_EXTENSIONS, \
    find_links_to_subpages, \
    find_links_in_page_with_urllib, \
    collect_all_subpages_urls

from main_anticor_div import find_anticorruption_div



def check_link_svedenia_o_doxodax(text):
    text = text.strip(' \n\t\r').strip('"').lower()
    text = " ".join(text.split()).replace("c","с").replace("e","е").replace("o","о")

    if text.startswith(u'сведения о доходах'):
        return True

    if text.startswith(u'сведения') and text.find("коррупц") != -1:
        return True;
    return False


def find_declarations_div(offices, only_missing=False):
    for office_info in offices:
        existing_link = office_info.get('declarations_div', {})
        if existing_link.get('engine', '') == 'manual':
            sys.stderr.write("skip manual url updating " + url + "\n")
            continue
        if len(existing_link.get('links', [])) > 0 and only_missing:
            continue
        links = office_info.get('anticorruption_div', {}).get('links', [])
        if len(links) == 0:
            links =  [office_info]
        for l in links:
            sys.stderr.write("process " + l['url'] + "\n")
            get_links(office_info, 'declarations_div', l['url'], check_link_svedenia_o_doxodax)

    write_offices(offices)


def go_through_pagination(offices):
    for office_info in offices:
        decl_div = office_info.get('declarations_div', {})
        decl_div_url = decl_div.get('url', '')
        if decl_div_url == '':
            decl_div_url = office_info.get('anticorruption_div', {}).get('url', "")
        if decl_div_url == '':
            sys.stderr.write("skip url " + office_info['url'] + " (do not know the start page)\n")

        all_links = collect_all_subpages_urls(decl_div_url)
        office_info['declarations_div_pages'] = list(all_links)

    write_offices(offices)

def check_download_text(text, href=None):
    text = text.strip(' \n\t\r').strip('"').lower()
    if text.startswith(u'скачать'):
        return True
    if text.startswith(u'загрузить'):
        return True

    if href != None:
        global OFFICE_FILE_EXTENSIONS
        for e in OFFICE_FILE_EXTENSIONS:
            if text.startswith(e[1:]):  #without "."
                return True
            if text.find(e) != -1:
                return True
            if href.lower().endswith(e):
                return True
        return False


def check_declaration_link_text(href, text):
    text = text.strip(' \n\t\r').lower()
    if text.startswith(u'приказ'):
        return True
    if text.startswith(u'распоряжение'):
        return True
    if check_download_text(text):
        return True
    return False


def find_declaration_urls(offices):
    for office_info in offices:
        docs = set()
        for url in office_info.get('declarations_div_pages', []):
            sys.stderr.write(url + "\n")
            new_docs = find_links_in_page_with_urllib(url, check_decree_link_text)
            docs = docs.union(new_docs)

        additional_docs = set()
        for url in docs:
            sys.stderr.write("download " +  url + "\n")
            try:
                new_docs =  find_links_in_page_with_urllib(url, check_download_text)
                additional_docs = additional_docs.union(new_docs)
            except  Exception as err:
                sys.stderr.write("cannot download " + url + ": " + str(err) + "\n")
                pass

        for url in additional_docs:
            sys.stderr.write("download additional " + url + "\n")
            try:
                download_with_cache(url)
            except  Exception as err:
                sys.stderr.write("cannot download " + url + ": " + str(err) + "\n")
                pass

        docs = docs.union(additional_docs)
        office_info['declarations'] = [x for x in docs]
        break
    write_offices(offices)



if __name__ == "__main__":
    #offices = create_office_list()
    offices = read_office_list()
    #find_anticorruption_div(offices, True)
    find_declarations_div(offices, True)
    go_through_pagination(offices)

    find_declaration_urls(offices)
    #find_declaration_urls(offices)
