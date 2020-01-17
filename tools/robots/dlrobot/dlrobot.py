import sys
import re
import os
import argparse
import logging

sys.path.append('../common')

from download import  download_page_collection, export_files_to_folder, get_file_extension_by_url, \
    get_all_sha256, get_site_domain_wo_www, DEFAULT_HTML_EXTENSION

from office_list import  TRobotProject

from find_link import \
    find_links_for_all_websites, \
    check_anticorr_link_text, \
    ACCEPTED_DECLARATION_FILE_EXTENSIONS, \
    check_self_link, \
    collect_subpages, \
    check_sub_page_or_iframe


def setup_logging(args,  logger):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(args.logfile):
        os.remove(args.logfile)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(args.logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

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

    if re.search('(сведения)|(справк[аи]) о доходах', text) is not None:
        return True

    if text.startswith(u'сведения') and text.find("коррупц") != -1:
        return True
    return False


def check_year_or_subpage(link_info):
    if check_sub_page_or_iframe(link_info):
        return True

    # here is a place for ML
    if link_info.Text is not None:
        text = link_info.Text.strip(' \n\t\r').strip('"').lower()
        if text.find('сведения') != -1:
            return True
    if link_info.Target is not None:
        target = link_info.Target.lower()
        if re.search('(^sved)|(sveodoh)|(do[ck]?[hx]od)|(income)', target) is not None:
            return True

    return False


def check_download_text(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.find('шаблоны') != -1:
        return False
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
            return ext != DEFAULT_HTML_EXTENSION
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



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    parser.add_argument("--rebuild", dest='rebuild', default=False, action="store_true")
    parser.add_argument("--step", dest='step', default=None)
    parser.add_argument("--start-from", dest='start_from', default=None)
    parser.add_argument("--stop-after", dest='stop_after', default=None)
    parser.add_argument("--from-human", dest='from_human_file_name', default=None)
    parser.add_argument("--logfile", dest='logfile', default="dlrobot.log")
    parser.add_argument("--input-url-list", dest='hypots', default=None)
    parser.add_argument("--smart-parser-binary",
                        dest='smart_parser_binary',
                        default="C:\\tmp\\smart_parser\\smart_parser\\src\\bin\\Release\\netcoreapp3.1\\smart_parser.exe")
    parser.add_argument("--result-folder", dest='result_folder', default="result")
    args = parser.parse_args()
    assert os.path.exists(args.smart_parser_binary)
    return args



if __name__ == "__main__":
    args = parse_args()
    if args.step is  not None:
        args.start_from = args.step
        args.stop_after = args.step
    logger = logging.getLogger("dlrobot_logger")
    setup_logging(args, logger)
    project = TRobotProject(args.project)
    if args.hypots is not None:
        if args.start_from is not None:
            logger.info("ignore --input-url-list since --start-from  or --step is specified")
        else:
            project.create_by_hypots(args.hypots)
    else:
        #project.create_office_list_by_consulant_ru()
        project.read_office_list()


    steps = [
        (find_links_for_all_websites, "sitemap", check_link_sitemap, "always"),
        (find_links_for_all_websites, "anticorruption_div", check_anticorr_link_text, "copy_if_empty"),
        (find_links_for_all_websites, "declarations_div", check_link_svedenia_o_doxodax, "copy_if_empty"),
        (collect_subpages, "declarations_div_pages", check_year_or_subpage, "always"),
        (find_links_for_all_websites, "declarations_div_pages2", check_documents, "always"),
        (find_links_for_all_websites, "declarations", check_accepted_declaration_file_type, "copy_docs"),
    ]
    prev_step = "morda"
    found_start_from = args.start_from is None
    for step_function, step_name, check_link_func, include_source in steps:
        if args.start_from is not None and step_name == args.start_from:
            found_start_from = True

        if found_start_from:
            if args.rebuild:
                project.del_old_info(step_name)
            logger.info("=== step {0} =========".format(step_name))
            step_function(project.offices, prev_step, step_name, check_link_func, include_source=include_source)
            project.write_offices()
        if args.stop_after is not None and step_name == args.stop_after:
            break

        prev_step = step_name

    if args.stop_after is None:
        last_step = steps[-1][1]
        logger.info("=== download all declarations =========")
        download_page_collection(project.offices, last_step)
        export_files_to_folder(project.offices, last_step, args.smart_parser_binary, args.result_folder)
        project.write_offices()
        if args.from_human_file_name is not None:
            project.check_all_offices(last_step)
