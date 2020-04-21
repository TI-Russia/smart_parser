import re
import os
import argparse
import logging
import datetime
from tempfile import TemporaryDirectory

from robots.common.download import  get_file_extension_by_url, DEFAULT_HTML_EXTENSION
from robots.common.export_files import export_files_to_folder
from robots.common.office_list import  TRobotProject
from ConvStorage.conversion_client import wait_doc_conversion_finished, assert_declarator_conv_alive
from DeclDocRecognizer.document_types import SOME_OTHER_DOCUMENTS
from robots.common.find_link import \
    check_anticorr_link_text, \
    ACCEPTED_DECLARATION_FILE_EXTENSIONS, \
    check_self_link, \
    check_sub_page_or_iframe, common_link_check


def setup_logging(logger, logfilename):
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)


def normalize_anchor_text(text):
    if text is not None:
        text = text.strip(' \n\t\r').strip('"').lower()
        text = " ".join(text.split()).replace("c", "с").replace("e", "е").replace("o", "о")
        return text
    return ""

def check_link_sitemap(link_info):
    if not check_self_link(link_info):
        return False
    text = normalize_anchor_text(link_info.Text)
    return text.startswith('карта сайта')


def check_link_svedenia_o_doxodax(link_info):
    if not check_self_link(link_info):
        return False

    text = normalize_anchor_text(link_info.Text)

    if text.find('координат') != -1:
        return False
    if text.find('заседании') != -1:
        return False
    if text.find('приказ') != -1:
        return False


    if re.search('((сведения)|(справк[аи])) о доходах', text) is not None:
        return True

    #http://arshush.ru/index.php?option=com_content&task=blogcategory&id=62&Itemid=72
    # "Сведения за 2018 год"
    if re.search('сведения.*20[0-9][0-9]', text) is not None:
        return True

    if text.startswith('сведения') and text.find("коррупц") != -1:
        return True
    return False


def declarations_div_pages_step(link_info):
    if check_sub_page_or_iframe(link_info):
        return True

    # here is a place for ML
    if link_info.Text is not None:
        text = normalize_anchor_text(link_info.Text)
        if text.find('должностях') != -1:
            return False
        if text.find('сведения') != -1:
            return True
        if text.find('справка о доходах') != -1:
            return True
        year_pattern = r'(20[0-9][0-9]( год)?)'
        if re.match('^' + year_pattern, text) is not None:
            return True
        if re.match(year_pattern + '$', text) is not None:
            return True
    if link_info.Target is not None:
        target = link_info.Target.lower()
        if re.search('(^sved)|(sveodoh)|(do[ck]?[hx]od)|(income)', target) is not None:
            return True

    return False


def check_documents(link_info):
    text = normalize_anchor_text(link_info.Text)
    if text.find("сведения") == -1:
        return False
    if link_info.Target is not None:
        return re.search('(docs)||(documents)|(files)', link_info.Target.lower()) is not None
    return True


def declaration_step_anchor_text(anchor_text):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS
    global SOME_OTHER_DOCUMENTS
    anchor_text = normalize_anchor_text(anchor_text)
    for typ in SOME_OTHER_DOCUMENTS:
        if anchor_text.find(typ) != -1:
            return False
    if anchor_text.startswith('скачать'):
        return True
    if anchor_text.startswith('загрузить'):
        return True

    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if e == DEFAULT_HTML_EXTENSION:
            continue
        # mos.ru: anchor text is "[ docx/ 1.1Mb ]Сведения"
        if anchor_text.find(e[1:]) != -1:
            return True
    return None # undef


def declaration_step_url(target_url):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS

    if target_url.find("download") != -1:
        return True  # otherwise ddos on admuni.ru
    if not common_link_check(target_url):
        return False  # to make faster

    # only office documents, not html, html must be checked by check_html_can_be_declaration
    if target_url.endswith('html'):
        return False

    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if e != DEFAULT_HTML_EXTENSION:
            if target_url.lower().endswith(e):
                return True
    try:
        ext = get_file_extension_by_url(target_url)
        return ext != DEFAULT_HTML_EXTENSION and ext in ACCEPTED_DECLARATION_FILE_EXTENSIONS
    except Exception as err:
        logger = logging.getLogger("dlrobot_logger")
        logger.error('cannot query (HEAD) url={}  exception={}\n'.format(target_url, str(err)))
        return False


def declaration_step(link_info):
    checked_by_text = declaration_step_anchor_text(link_info.Text)
    if checked_by_text is not None:
        return checked_by_text

    if link_info.DownloadedBySelenium is not None:
        return True

    if link_info.Target is not None:
        if declaration_step_url(link_info.Target):
            return True
    return False


def check_html_can_be_declaration(html):
    html = html.lower()
    words = html.find('квартир') != -1 and html.find('доход') != -1 and html.find('должность') != -1
    numbers = re.search('[0-9]{6}', html) is not None # доход
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
        'include_sources': "copy_if_empty",
        'search_engine_request': "противодействие коррупции",
        'min_normal_count': 1
    },
    {
        'step_name': "declarations_div",
        'check_link_func': check_link_svedenia_o_doxodax,
        'include_sources': "copy_if_empty",
        'do_not_copy_urls_from_steps': [None, 'sitemap'], # None is for morda_url
        'search_engine_request': '"сведения о доходах"',
        'min_normal_count': 5
    },
    {
        'step_name': "declarations_div_pages",
        'check_link_func': declarations_div_pages_step,
        'include_sources': "always",
        'transitive': True,
        'fallback_to_selenium': False
    },
    {
        'step_name': "declarations_div_pages2",
        'check_link_func': check_documents,
        'include_sources': "always"
    },
    {
        'step_name': "declarations",
        'check_link_func': declaration_step,
        'check_html_sources': check_html_can_be_declaration,
        'include_sources': "copy_missing_docs",
        'search_engine_request': '"сведения о доходах"',
        'min_normal_count': 3
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
    parser.add_argument("--click-features", dest='click_features_file', default=None)
    parser.add_argument("--result-folder", dest='result_folder', default="result")
    args = parser.parse_args()
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
                logger.info(office_info.get_domain_name())

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
        logger.info("=== wait for all document conversion finished =========")
        wait_doc_conversion_finished()

    logger.info("=== export_files_to_folder =========")
    export_files_to_folder(project.offices, args.result_folder)
    project.write_export_stats()
    project.write_project()


def open_project(args, log_file_name):
    logger = logging.getLogger("dlrobot_logger")
    setup_logging(logger, log_file_name)
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
    assert_declarator_conv_alive()
    if args.logfile == "temp":
        with TemporaryDirectory(prefix="tmp_dlrobot_log", dir=".") as tmp_folder:
            log_file_name = os.path.join(tmp_folder, "dlrobot.log")
            open_project(args, log_file_name)
            logging.shutdown()
    else:
        open_project(args, args.logfile)

