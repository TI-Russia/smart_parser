import sys
import re
import argparse
sys.path.append('../common')

from download import  download_page_collection, export_files_to_folder, get_file_extension_by_url

from office_list import  create_office_list, read_office_list, write_offices

from find_link import \
    find_links_for_all_websites, \
    check_anticorr_link_text, \
    OFFICE_FILE_EXTENSIONS, \
    check_self_link, \
    collect_subpages, \
    check_sub_page


def check_link_sitemap(link_info):
    if not check_self_link(link_info):
        return False

    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    text = " ".join(text.split()).replace("c","с").replace("e","е").replace("o","о")

    return text.startswith(u'карта сайта')


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

def check_office_document(link_info):
    if check_download_text(link_info):
        return True
    if link_info.Target is not None:
        ext = get_file_extension_by_url(link_info.Target)
        return ext != ".html"
    return False

def check_documents(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.find("сведения") == -1:
        return False
    if link_info.Target is not None:
        return re.search('(documents)|(files)', link_info.Target.lower()) is not None
    return True


def del_old_info(offices, step_name):
    for office_info in offices:
        if step_name in office_info:
            del (office_info[step_name])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    parser.add_argument("--rebuild", dest='rebuild', default=False, action="store_true")
    parser.add_argument("--start-from", dest='start_from', default=None)
    return parser.parse_args()



if __name__ == "__main__":
    args = parse_args()
    #offices = create_office_list(args.project)
    offices = read_office_list(args.project)

    steps = [
        (find_links_for_all_websites, "sitemap", check_link_sitemap),
        (find_links_for_all_websites, "anticorruption_div", check_anticorr_link_text),
        (find_links_for_all_websites, "declarations_div", check_link_svedenia_o_doxodax),
        (collect_subpages, "declarations_div_pages", check_sub_page),
        (find_links_for_all_websites, "declarations_div_pages2", check_documents),
        (find_links_for_all_websites, "declarations", check_office_document),
    ]
    prev_step = "morda"
    found_start_from = args.start_from is None
    for step_function, step_name, check_link_func in steps:
        if args.start_from is not None and step_name == args.start_from:
            found_start_from = True

        if found_start_from:
            if args.rebuild:
                del_old_info(offices, step_name)
            print ("=== step {0} =========".format(step_name))
            step_function(offices, prev_step, step_name, check_link_func)
            write_offices(offices, args.project)

        prev_step = step_name


    download_page_collection(offices, prev_step)
    export_files_to_folder(offices, prev_step, "result")
