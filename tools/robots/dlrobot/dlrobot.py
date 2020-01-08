import sys
import re
import json
import os
import argparse
from urllib.parse import urlparse
import logging

sys.path.append('../common')

from download import  download_page_collection, export_files_to_folder, get_file_extension_by_url, \
    get_all_sha256

from office_list import  create_office_list, read_office_list, write_offices

from find_link import \
    find_links_for_all_websites, \
    check_anticorr_link_text, \
    ACCEPTED_DECLARATION_FILE_EXTENSIONS, \
    check_self_link, \
    collect_subpages, \
    check_sub_page_or_iframe

def setup_logging(args):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(args.logfile):
        os.remove(args.logfile)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(args.logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    #ch.setFormatter(formatter)
    root.addHandler(ch)

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

    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if text.startswith(e[1:]):  #without "."
            return True
        if text.find(e) != -1:
            return True
        if link_info.Target is not None and link_info.Target.lower().endswith(e):
            return True
    return False


def check_accepted_declaration_file_type(link_info):
    if check_download_text(link_info):
        return True
    if link_info.Target is not None:
        try:
            if link_info.DownloadFile is not None:
                return True
            ext = get_file_extension_by_url(link_info.Target)
            return ext != ".html"
        except Exception as err:
            sys.stderr.write('cannot query (HEAD) url={0}  exception={1}\n'.format(link_info.Target, str(err)))
            return False
    return False


def check_documents(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.find("сведения") == -1:
        return False
    if link_info.Target is not None:
        return re.search('(docs)||(documents)|(files)', link_info.Target.lower()) is not None
    return True


def del_old_info(offices, step_name):
    for office_info in offices:
        if step_name in office_info:
            del (office_info[step_name])


def strip_domain(domain):
    if domain.startswith('www.'):
        domain = domain[len('www.'):]
    return domain


class THumanFiles:
    def __init__(self):
        self.files = list()

    def read_from_file(self, filename):
        with open(filename, "r", encoding="utf8") as inpf:
            self.files = json.load(inpf)

    def check_all_offices(self, offices, page_collection_name):
        for o in offices:
            main_url = list(o['morda']['links'])[0]
            main_domain = strip_domain(urlparse(main_url).netloc)
            logging.debug("check_recall for {}".format(main_domain))
            robot_sha256 = get_all_sha256(o, page_collection_name)
            files_count = 0
            found_files_count = 0
            for x in self.files:
                if len(x['domain']) > 0:
                    domain = strip_domain(x['domain'])
                    if domain == main_domain or main_domain.endswith(domain) or domain.endswith(main_domain):
                        for s in x['sha256']:
                            files_count += 1
                            if s not in robot_sha256:
                                logging.debug("{0} not found from {1}".format(s, json.dumps(x)))
                            else:
                                found_files_count += 1
            logging.info("all human files = {}, human files found by dlrobot = {}".format(files_count, found_files_count))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    parser.add_argument("--rebuild", dest='rebuild', default=False, action="store_true")
    parser.add_argument("--start-from", dest='start_from', default=None)
    parser.add_argument("--stop-after", dest='stop_after', default=None)
    parser.add_argument("--from-human", dest='from_human_file_name', default=None)
    parser.add_argument("--logfile", dest='logfile', default="dlrobot.log")
    return parser.parse_args()



if __name__ == "__main__":
    args = parse_args()
    setup_logging(args)
    human_files = THumanFiles()
    if args.from_human_file_name is not None:
        human_files.read_from_file(args.from_human_file_name)
    #offices = create_office_list(args.project)
    offices = read_office_list(args.project)

    steps = [
        (find_links_for_all_websites, "sitemap", check_link_sitemap, "always"),
        (find_links_for_all_websites, "anticorruption_div", check_anticorr_link_text, "copy_if_empty"),
        (find_links_for_all_websites, "declarations_div", check_link_svedenia_o_doxodax, "copy_if_empty"),
        (collect_subpages, "declarations_div_pages", check_sub_page_or_iframe, "always"),
        (find_links_for_all_websites, "declarations_div_pages2", check_documents, "always"),
        (find_links_for_all_websites, "declarations", check_accepted_declaration_file_type, "never"),
    ]
    prev_step = "morda"
    found_start_from = args.start_from is None
    for step_function, step_name, check_link_func, include_source in steps:
        if args.start_from is not None and step_name == args.start_from:
            found_start_from = True

        if found_start_from:
            if args.rebuild:
                del_old_info(offices, step_name)
            logging.info("=== step {0} =========".format(step_name))
            step_function(offices, prev_step, step_name, check_link_func, include_source=include_source)
            write_offices(offices, args.project)
        if args.stop_after is not None and step_name == args.stop_after:
            break

        prev_step = step_name

    if args.stop_after is None:
        last_step = steps[-1][1]
        download_page_collection(offices, last_step)
        export_files_to_folder(offices, last_step, "result")
        if args.from_human_file_name is not None:
            human_files.check_all_offices(offices, last_step)
