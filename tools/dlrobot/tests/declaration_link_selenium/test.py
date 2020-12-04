import urllib
import os
from common.download import TDownloadEnv
from common.robot_step import TRobotStep, TUrlInfo
from common.robot_project import TRobotProject
from dlrobot.declaration_link import looks_like_a_declaration_link
from common.http_request import TRequestPolicy
import logging
import argparse
#import yappi

ROBOT_STEPS = [
    {
        'step_name': "declarations",
        'check_link_func': looks_like_a_declaration_link,
        'fallback_to_selenium': True,
        'use_urllib': False
    }
]


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
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-page", dest='start_page', required=True)
    parser.add_argument("--project", dest='project', required=False, default="project.txt")
    return parser.parse_args()


def open_project(args):
    start_url = args.start_page
    with TRobotProject(logger, args.project, ROBOT_STEPS, "result", enable_search_engine=False,
                       ) as project:
        project.read_project(True)
        office_info = project.offices[0]
        office_info.create_export_folder()
        office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

        step_info = TRobotStep(office_info, ROBOT_STEPS[0])
        step_info.pages_to_process[start_url] = 0
        step_info.processed_pages = set()

        #yappi.start()
        step_info.make_one_step()
        #print_all(yappi.get_func_stats())

        for url in step_info.step_urls:
            u = list(urllib.parse.urlparse(url))
            u[1] = "dummy"
            print (urllib.parse.urlunparse(u))


def print_all(stats):
    if stats.empty():
        return
    sizes = [136, 5, 8, 8, 8]
    columns = dict(zip(range(len(yappi.COLUMNS_FUNCSTATS)), zip(yappi.COLUMNS_FUNCSTATS, sizes)))
    show_stats = stats
    with open ('yappi.log', 'w') as outp:
        outp.write(os.linesep)
        for stat in show_stats:
            stat._print(outp, columns)


if __name__ == '__main__':
    logger = setup_logging("dlrobot.log")
    args = parse_args()
    TDownloadEnv.clear_cache_folder()
    TRequestPolicy.ENABLE = False
    open_project(args)
