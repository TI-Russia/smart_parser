from common.download import TDownloadEnv
from web_site_db.robot_project import TRobotProject
from web_site_db.robot_step import TRobotStep
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from common.link_info import check_link_sitemap, check_anticorr_link_text
from common.primitives import convert_timeout_to_seconds
from common.http_request import THttpRequester
from dl_robot.declaration_link import looks_like_a_declaration_link
from common.logging_wrapper import setup_logging

import platform
import tempfile
import os
import sys
import argparse
import traceback


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


class TDlrobot:
    @staticmethod
    def parse_args(arg_list):
        global ROBOT_STEPS
        parser = argparse.ArgumentParser()
        parser.add_argument("--project", dest='project', default="web_site_snapshots.txt", required=True)
        parser.add_argument("--step", dest='step', default=None)
        parser.add_argument("--start-from", dest='start_from', default=None)
        parser.add_argument("--stop-after", dest='stop_after', default=None)
        parser.add_argument("--logfile", dest='logfile', default=None)
        parser.add_argument("--click-features", dest='click_features_file', default=None)
        parser.add_argument("--result-folder", dest='result_folder', default="result")
        parser.add_argument("--clear-cache-folder", dest='clear_cache_folder', default=False, action="store_true")
        parser.add_argument("--cache-folder-tmp", dest='cache_folder_tmp', default=False, action="store_true",
                                help="create cache folder as a tmp folder and delete it upon exit")
        parser.add_argument("--max-step-urls", dest='max_step_url_count', default=1000, type=int)
        parser.add_argument("--only-click-paths", dest='only_click_paths', default=False, action="store_true")
        parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                                default="3h",
                                help="crawling timeout in seconds (there is also conversion step after crawling)")
        parser.add_argument("--last-conversion-timeout", dest='last_conversion_timeout',
                                default="30m",
                                help="pdf conversion timeout after crawling")
        parser.add_argument("--total-timeout", dest='total_timeout',
                            default="4h",
                            help="dlrobot must finish its work in this time otherwise it would be killed externally")
        parser.add_argument("--pdf-quota-conversion", dest='pdf_quota_conversion',
                                default=20 * 2**20,
                                type=int,
                                help="max sum pdf size to end ")
        args = parser.parse_args(arg_list)
        TRobotStep.max_step_url_count = args.max_step_url_count
        if args.step is  not None:
            args.start_from = args.step
            args.stop_after = args.step
        if args.logfile is None:
            args.logfile = args.project + ".log"
        TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT = convert_timeout_to_seconds(args.crawling_timeout)
        if TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT > TWebSiteCrawlSnapshot.DEFAULT_CRAWLING_TIMEOUT:
            TWebSiteCrawlSnapshot.SINGLE_DECLARATION_TIMEOUT = 60 * 60
        TDownloadEnv.LAST_CONVERSION_TIMEOUT = convert_timeout_to_seconds(args.last_conversion_timeout)
        TDownloadEnv.PDF_QUOTA_CONVERSION = args.pdf_quota_conversion
        return args

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name=args.logfile)
        self.logger.debug("TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT={}".format(TWebSiteCrawlSnapshot.CRAWLING_TIMEOUT))
        TDownloadEnv.init_conversion(self.logger)
        THttpRequester.initialize(self.logger)
        if args.clear_cache_folder:
            TDownloadEnv.clear_cache_folder()

    def step_index_by_name(self, name):
        if name is None:
            return -1
        for i, r in enumerate(ROBOT_STEPS):
            if name == r['step_name']:
                return i
        raise Exception("cannot find step {}".format(name))

    def make_steps(self, project):
        if self.args.start_from != "last_step":
            start = self.step_index_by_name(self.args.start_from) if self.args.start_from is not None else 0
            end = self.step_index_by_name(self.args.stop_after) + 1 if self.args.stop_after is not None else len(ROBOT_STEPS)
            for step_no in range(start, end):
                for web_site in project.web_site_snapshots:
                    web_site.find_links_for_one_website(step_no)
                project.write_project()

        if self.args.stop_after is not None:
            if self.args.stop_after != "last_step":
                return

        self.logger.info("=== wait for all document conversion finished =========")
        TDownloadEnv.CONVERSION_CLIENT.wait_doc_conversion_finished(TDownloadEnv.LAST_CONVERSION_TIMEOUT)

        self.logger.info("=== export_files_to_folder =========")
        project.export_files_to_folder()
        project.write_project()

    def open_project(self):
        self.logger.debug("hostname={}".format(platform.node()))
        self.logger.debug("use {} as a cache folder".format(os.path.realpath(TDownloadEnv.FILE_CACHE_FOLDER)))
        with TRobotProject(self.logger, self.args.project, ROBOT_STEPS, self.args.result_folder) as project:
            project.total_timeout = convert_timeout_to_seconds(self.args.total_timeout)
            self.logger.debug("total_timeout = {}".format(self.args.total_timeout))
            project.read_project()
            project.fetch_main_pages()
            if self.args.only_click_paths:
                project.write_export_stats()
            else:
                self.make_steps(project)
                project.write_export_stats()
                if self.args.click_features_file:
                    project.write_click_features(self.args.click_features_file)
            return project


if __name__ == "__main__":
    dlrobot = TDlrobot(TDlrobot.parse_args(sys.argv[1:]))
    try:
        if dlrobot.args.cache_folder_tmp:
            with tempfile.TemporaryDirectory(prefix="cached.", dir=".") as TDownloadEnv.FILE_CACHE_FOLDER:
                dlrobot.open_project()
        else:
            dlrobot.open_project()
    except Exception as e:
        print("unhandled exception type={}, exception={} ".format(type(e), e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except KeyboardInterrupt:
        print("ctrl+c received")
        sys.exit(1)
    finally:
        if TDownloadEnv.CONVERSION_CLIENT is not None:
            TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
