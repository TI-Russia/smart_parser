import sys
import re
import os
import argparse
import logging
import datetime
from tempfile import TemporaryDirectory

sys.path.append('../common')

from download import  export_files_to_folder, get_file_extension_by_url, \
    get_site_domain_wo_www, DEFAULT_HTML_EXTENSION

from office_list import  TRobotProject

from find_link import \
    check_anticorr_link_text, \
    ACCEPTED_DECLARATION_FILE_EXTENSIONS, \
    check_self_link, \
    check_sub_page_or_iframe



def setup_logging(args,  logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(args.logfile):
        os.remove(args.logfile)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename)
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


def check_documents(link_info):
    text = link_info.Text.strip(' \n\t\r').strip('"').lower()
    if text.find("сведения") == -1:
        return False
    if link_info.Target is not None:
        return re.search('(docs)||(documents)|(files)', link_info.Target.lower()) is not None
    return True


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


def check_html_can_be_declaration(html):
    html = html.lower()
    words = html.find('квартира') != -1 and html.find('доход')!=-1 and html.find('должность')!= -1
    numbers = re.search('[0-9]{6}', html) != None # доход
    return words and numbers


ROBOT_STEPS = [
    {
        'step_name': "sitemap",
        'check_link_func': check_link_sitemap,
        'include_sources': 'always'
    },
    {
        'step_name': "anticorruption_div",
        'check_link_func': check_anticorr_link_text,
        'search_engine_request': "противодействие коррупции",
        'include_sources': "copy_if_empty"
    },
    {
        'step_name': "declarations_div",
        'check_link_func': check_link_svedenia_o_doxodax,
        'include_sources': "copy_if_empty",
        'do_not_copy_urls_from_steps': [None, 'sitemap'] # None is for morda_url
    },
    {
        'step_name': "declarations_div_pages",
        'check_link_func': check_year_or_subpage,
        'include_sources': "always",
        'transitive': True,
        'only_missing': False,
        'fallback_to_selenium': False
    },
    {
        'step_name': "declarations_div_pages2",
        'check_link_func': check_documents,
        'include_sources': "always"
    },
    {
        'step_name': "declarations",
        'check_link_func': check_accepted_declaration_file_type,
        'check_html_sources': check_html_can_be_declaration,
        'include_sources': "never"
    },
]


def parse_args():
    global ROBOT_STEPS
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    parser.add_argument("--skip-final-download", dest='skip_final_download', default=False, action="store_true")
    parser.add_argument("--step", dest='step', default=None)
    parser.add_argument("--start-from", dest='start_from', default=None)
    parser.add_argument("--stop-after", dest='stop_after', default=None)
    parser.add_argument("--from-human", dest='from_human_file_name', default=None)
    parser.add_argument("--logfile", dest='logfile', default="dlrobot.log")
    parser.add_argument("--input-url-list", dest='hypots', default=None)
    parser.add_argument("--smart-parser-binary",
                        dest='smart_parser_binary',
                        default="C:\\tmp\\smart_parser\\smart_parser\\src\\bin\\Release\\netcoreapp3.1\\smart_parser.exe")
    parser.add_argument("--click-features", dest='click_features_file', default=None)
    parser.add_argument("--result-folder", dest='result_folder', default="result")
    args = parser.parse_args()
    assert os.path.exists(args.smart_parser_binary)
    if args.step is  not None:
        args.start_from = args.step
        args.stop_after = args.step
    return args

def step_index_by_name(name):
    if name is None:
        return -1
    for i, r in enumerate(ROBOT_STEPS):
        if name == r['step_name']:
            return i
    raise Exception("cannot find step {}".format(name))

def make_steps(args, project):
    logger = logging.getLogger("dlrobot_logger")
    if args.start_from != "last_step":
        start = step_index_by_name(args.start_from) if args.start_from is not None else 0
        end = step_index_by_name(args.stop_after) + 1 if args.stop_after is not None else len(ROBOT_STEPS)
        for step_passport in ROBOT_STEPS[start:end]:
            step_name = step_passport['step_name']
            logger.info("=== step {0} =========".format(step_name))
            for office_info in project.offices:
                start = datetime.datetime.now()
                logger.info('{0}'.format(get_site_domain_wo_www(office_info.morda_url)))

                project.find_links_for_one_website(office_info, step_passport)

                logger.info("step elapsed time {} {} {}".format(
                    office_info.morda_url,
                    step_name,
                    (datetime.datetime.now() - start).total_seconds()))

            project.write_project()

    if args.stop_after is not None:
        if args.stop_after != "last_step":
            return

    if not args.skip_final_download:
        logger.info("=== download all declarations =========")
        project.download_last_step()
        export_files_to_folder(project.offices, args.smart_parser_binary, args.result_folder)
        project.write_export_stats()
        project.write_project()


def open_project(args, log_file_name):
    logger = logging.getLogger("dlrobot_logger")
    setup_logging(args, logger, log_file_name)
    with TRobotProject(args.project, ROBOT_STEPS) as project:
        if args.hypots is not None:
            if args.start_from is not None:
                logger.info("ignore --input-url-list since --start-from  or --step is specified")
            else:
                project.create_by_hypots(args.hypots)
        else:
            project.read_project()

        make_steps(args, project)

        if args.from_human_file_name is not None:
            project.check_all_offices()
        if args.click_features_file:
            project.write_click_features(args.click_features_file)

if __name__ == "__main__":
    args = parse_args()
    if  args.logfile == "temp":
        with TemporaryDirectory(prefix="tmp_dlrobot_log", dir=".") as tmp_folder:
            log_file_name = os.path.join(tmp_folder, "dlrobot.log")
            open_project(args, log_file_name)
            logging.shutdown()
    else:
        open_project(args, args.logfile)

