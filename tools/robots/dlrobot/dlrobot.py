import re
import os
import argparse
import logging
import datetime
import sys
import traceback
from tempfile import TemporaryDirectory
import urllib.error
from robots.common.download import  get_file_extension_only_by_headers, DEFAULT_HTML_EXTENSION, CONVERSION_CLIENT
from robots.common.export_files import export_files_to_folder
from robots.common.office_list import  TRobotProject
from DeclDocRecognizer.document_types import SOME_OTHER_DOCUMENTS
from robots.common.content_types import ACCEPTED_DECLARATION_FILE_EXTENSIONS
from robots.common.primitives import normalize_anchor_text, check_link_sitemap, check_anticorr_link_text, \
                                    check_sub_page_or_iframe
from robots.common.http_request import HttpHeadException
from ConvStorage.conversion_client import TDocConversionClient

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


NEGATIVE_WORDS = [
    'координат',  'заседании',
    #'должност', # замещающих должности
    'выборы',    'памятка',    'доклад',
    'конкурс',    'пресс-релиз',    'правила',
    'положение',    'методические',    'заявление',
    'схема',    'концепция',    'доктрина',
    'технические',    '^федеральный',    '^историческ',
    '^закон',    'новости', "^формы", "обратная", "обращения",
    "^перечень", "прочие", "слабовидящих"
] + SOME_OTHER_DOCUMENTS

NEGATIVE_REGEXP = re.compile("|".join(list("({})".format(x) for x in NEGATIVE_WORDS)))


def has_negative_words(anchor_text):
    global NEGATIVE_REGEXP
    return NEGATIVE_REGEXP.search(anchor_text) is not None


def looks_like_a_document_link(link_info):
    global ACCEPTED_DECLARATION_FILE_EXTENSIONS

    # check anchor text
    anchor_text = normalize_anchor_text(link_info.AnchorText)
    if re.search('(скачать)|(загрузить)', anchor_text) is not None:
        return True
    for e in ACCEPTED_DECLARATION_FILE_EXTENSIONS:
        if e == DEFAULT_HTML_EXTENSION:
            continue
        # mos.ru: anchor text is "[ docx/ 1.1Mb ]Сведения"
        if anchor_text.find(e[1:]) != -1:
            return True

    # check url path or make http head request
    if link_info.TargetUrl is not None:
        target = link_info.TargetUrl.lower()
        if re.search('(docs)|(documents)|(files)|(download)', target):
            return True
        if target.endswith('html') or target.endswith('htm'):
            return False
        try:
            ext = get_file_extension_only_by_headers(link_info.TargetUrl)
            return ext != DEFAULT_HTML_EXTENSION and ext in ACCEPTED_DECLARATION_FILE_EXTENSIONS
        except HttpHeadException as err:
            pass  # do not spam logs
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            logger = logging.getLogger("dlrobot_logger")
            logger.error('cannot query (HEAD) url={}  exception={}\n'.format(link_info.TargetUrl, err))
            return False

    return False


def looks_like_a_declaration_link(link_info):
    # here is a place for ML
    anchor_text = normalize_anchor_text(link_info.AnchorText)
    page_html = normalize_anchor_text(link_info.PageHtml)
    if has_negative_words(anchor_text):
        return False
    svedenia = re.search('сведения', anchor_text) is not None
    doc_type = re.search('(сведения)|(справк[аи])', anchor_text) is not None
    year_found = re.search('\\b20[0-9][0-9]\\b', anchor_text) is not None
    income_regexp = '(доход((ах)|(е)))|(коррупц)'
    income = re.search(income_regexp, page_html) is not None
    is_document_link = looks_like_a_document_link(link_info)
    is_a_sub_page = check_sub_page_or_iframe(link_info)
    income_in_url_path = False
    if link_info.TargetUrl is not None:
        target = link_info.TargetUrl.lower()
        if re.search('(^sved)|(sveodoh)', target):
            svedenia = True
        if re.search('(do[ck]?[hx]od)|(income)', target):
            income = True
            income_in_url_path = True
    all_features = (("income", income), ("doc_type", doc_type), ("year_found", year_found),
                     ("is_document_link", is_document_link), ("is_a_sub_page", is_a_sub_page),
                     ("income_in_url_path", income_in_url_path))
    positive_case = None
    if income and (doc_type or year_found or is_document_link or is_a_sub_page):
        positive_case = "case 1"
    elif income_in_url_path and is_a_sub_page:
        positive_case = "case 2"
    # http://arshush.ru/index.php?option=com_content&task=blogcategory&id=62&Itemid=72
    # "Сведения за 2018 год" and  no thematic word
    elif svedenia and (year_found or is_document_link):
        positive_case = "case 3"

    if positive_case is not None:
        all_features_str = ";".join(k for k, v in all_features if v)
        logging.getLogger("dlrobot_logger").debug("{}, features: {}".format(positive_case, all_features_str))
        return True
    return False


def check_html_can_be_declaration(html):
    # dl_recognizer is called afterwards
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
        'search_engine': {
            'request': "противодействие коррупции",
            'policy': "run_after_if_no_results",
            'max_serp_results': 1
        }
    },
    {
        'step_name': "declarations",
        'check_link_func': looks_like_a_declaration_link,
        'include_sources': "copy_if_empty",
        'do_not_copy_urls_from_steps': [None, 'sitemap'],  # None is for morda_url
        'search_engine': {
            'request': '"сведения о доходах"',
            'policy': "run_always_before"
        },
        'check_html_sources': check_html_can_be_declaration,
        'transitive': True,
    }
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
    global CONVERSION_CLIENT
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
    CONVERSION_CLIENT.wait_doc_conversion_finished()

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
    try:
        CONVERSION_CLIENT = TDocConversionClient()
        CONVERSION_CLIENT.start_conversion_thread()
        if args.logfile == "temp":
            with TemporaryDirectory(prefix="tmp_dlrobot_log", dir=".") as tmp_folder:
                log_file_name = os.path.join(tmp_folder, "dlrobot.log")
                open_project(args, log_file_name)
                logging.shutdown()
        else:
            open_project(args, args.logfile)
    except Exception as e:
        print("unhandled exception type={}, exception={} ".format(type(e), e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except KeyboardInterrupt:
        print("ctrl+c received")
        sys.exit(1)
    finally:
        CONVERSION_CLIENT.stop_conversion_thread()
