﻿import os
import argparse
import logging
import sys
import traceback
from robots.common.download import TDownloadEnv
from robots.common.robot_project import TRobotProject
from robots.common.robot_step import TRobotStep
from robots.common.web_site import TRobotWebSite
from robots.common.primitives import  check_link_sitemap, check_anticorr_link_text
from robots.dlrobot.declaration_link import looks_like_a_declaration_link
import platform

def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_logger")
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
    return logger


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
        'transitive': True,
    }
]


def convert_to_seconds(s):
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600}
    if s is None or len(s) == 0:
        return 0
    if seconds_per_unit.get(s[-1]) is not None:
        return int(s[:-1]) * seconds_per_unit[s[-1]]
    else:
        return int(s)

def parse_args():
    global ROBOT_STEPS
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", dest='project', default="offices.txt", required=True)
    parser.add_argument("--step", dest='step', default=None)
    parser.add_argument("--start-from", dest='start_from', default=None)
    parser.add_argument("--stop-after", dest='stop_after', default=None)
    parser.add_argument("--logfile", dest='logfile', default=None)
    parser.add_argument("--click-features", dest='click_features_file', default=None)
    parser.add_argument("--result-folder", dest='result_folder', default="result")
    parser.add_argument("--clear-cache-folder", dest='clear_cache_folder', default=False, action="store_true")
    parser.add_argument("--max-step-urls", dest='max_step_url_count', default=1000, type=int)
    parser.add_argument("--only-click-stats", dest='only_click_stats', default=False, action="store_true")
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            default="3h",
                            help="crawling timeout in seconds (there is also conversion step after crawling)")
    parser.add_argument("--last-conversion-timeout", dest='last_conversion_timeout',
                            default="30m",
                            help="pdf conversion timeout after crawling")
    parser.add_argument("--pdf-quota-conversion", dest='pdf_quota_conversion',
                            default=20 * 2**20,
                            type=int,
                            help="max sum pdf size to end ")
    args = parser.parse_args()
    TRobotStep.max_step_url_count = args.max_step_url_count
    if args.step is  not None:
        args.start_from = args.step
        args.stop_after = args.step
    if args.logfile is None:
        args.logfile = args.project + ".log"
    TRobotWebSite.CRAWLING_TIMEOUT = convert_to_seconds(args.crawling_timeout)
    TDownloadEnv.LAST_CONVERSION_TIMEOUT = convert_to_seconds(args.last_conversion_timeout)
    TDownloadEnv.PDF_QUOTA_CONVERSION = args.pdf_quota_conversion
    return args


def step_index_by_name(name):
    if name is None:
        return -1
    for i, r in enumerate(ROBOT_STEPS):
        if name == r['step_name']:
            return i
    raise Exception("cannot find step {}".format(name))


def make_steps(args, project):
    if args.start_from != "last_step":
        start = step_index_by_name(args.start_from) if args.start_from is not None else 0
        end = step_index_by_name(args.stop_after) + 1 if args.stop_after is not None else len(ROBOT_STEPS)
        for step_no in range(start, end):
            for office_info in project.offices:
                office_info.find_links_for_one_website(step_no)
            project.write_project()

    if args.stop_after is not None:
        if args.stop_after != "last_step":
            return

    project.logger.info("=== wait for all document conversion finished =========")
    TDownloadEnv.CONVERSION_CLIENT.wait_doc_conversion_finished(TDownloadEnv.LAST_CONVERSION_TIMEOUT)

    project.logger.info("=== export_files_to_folder =========")
    project.export_files_to_folder()
    project.write_project()


def open_project(args):
    logger = setup_logging(args.logfile)
    logger.debug("hostname={}".format(platform.node()))

    with TRobotProject(logger, args.project, ROBOT_STEPS, args.result_folder) as project:
        project.read_project()
        if args.only_click_stats:
            project.write_export_stats()
        else:
            make_steps(args, project)
            project.write_export_stats()
            if args.click_features_file:
                project.write_click_features(args.click_features_file)


if __name__ == "__main__":
    args = parse_args()
    if args.clear_cache_folder:
        TDownloadEnv.clear_cache_folder()
    try:
        TDownloadEnv.init_conversion()
        open_project(args)
    except Exception as e:
        print("unhandled exception type={}, exception={} ".format(type(e), e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except KeyboardInterrupt:
        print("ctrl+c received")
        sys.exit(1)
    finally:
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
