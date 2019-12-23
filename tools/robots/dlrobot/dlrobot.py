import sys
import re
import argparse
sys.path.append('../common')

from download import  download_page_collection, export_files_to_folder

from office_list import  create_office_list, read_office_list, write_offices

from find_link import \
    find_links_for_all_websites, \
    check_anticorr_link_text, \
    OFFICE_FILE_EXTENSIONS, \
    check_self_link, \
    collect_subpages


def check_link_svedenia_o_doxodax(link_info):
    if not check_self_link(link_info):
        return False

    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    text = " ".join(text.split()).replace("c","с").replace("e","е").replace("o","о")

    if text.startswith(u'сведения о доходах'):
        return True

    if text.startswith(u'сведения') and text.find("коррупц") != -1:
        return True;
    return False



def check_download_text(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.startswith(u'скачать'):
        return True
    if text.startswith(u'загрузить'):
        return True

    global OFFICE_FILE_EXTENSIONS
    for e in OFFICE_FILE_EXTENSIONS:
        if text.startswith(e[1:]):  #without "."
            return True
        if text.find(e) != -1:
            return True
        if link_info.Target is not None and link_info.Target.lower().endswith(e):
            return True
    return False


def check_documents(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.find("сведения") == -1:
        return False
    if link_info.Target is not None:
        return re.search('(documents)|(files)', link_info.Target.lower()) is not None
    return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    #offices = create_office_list(args.project)
    offices = read_office_list(args.project)
    find_links_for_all_websites(offices, "morda", "anticorruption_div", check_anticorr_link_text)
    write_offices(offices, args.project)
    find_links_for_all_websites(offices, "anticorruption_div", "declarations_div", check_link_svedenia_o_doxodax)
    write_offices(offices, args.project)

    collect_subpages(offices, "declarations_div", "declarations_div_pages")
    write_offices(offices, args.project)
    find_links_for_all_websites(offices, "declarations_div_pages", "declarations_div_pages2", check_documents)
    write_offices(offices, args.project)
    find_links_for_all_websites(offices, "declarations_div_pages2", "declarations", check_download_text)
    write_offices(offices, args.project)
    download_page_collection(offices, "declarations")
    write_offices(offices, args.project)
    export_files_to_folder(offices, "declarations", "result")
