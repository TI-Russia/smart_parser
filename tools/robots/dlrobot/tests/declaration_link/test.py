import http.server
import sys
import os
import threading
from robots.common.download import get_file_extension_only_by_headers, TDownloadedFile, \
             DEFAULT_HTML_EXTENSION, TDownloadEnv
from robots.common.robot_step import TRobotStep, TUrlInfo
from robots.common.robot_project import TRobotProject
from robots.dlrobot.declaration_link import looks_like_a_declaration_link
from robots.common.http_request import TRequestPolicy
import logging
import argparse
import time


class THttpServer(http.server.BaseHTTPRequestHandler):
    INIT_PAGE_FILE_PATH = ""
    INIT_URL_PATH = '/init.html'
    def build_headers(self, content_type="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def do_GET(self):
        self.build_headers()
        if self.path == THttpServer.INIT_URL_PATH:
            with open(THttpServer.INIT_PAGE_FILE_PATH, "r", encoding="utf8") as inp:
                self.wfile.write(inp.read().encode('utf8'))
        else:
            self.wfile.write("some text".encode('utf8'))

    def do_HEAD(self):
        if self.path.endswith('.docx'):
            self.build_headers("application/vnd.openxmlformats-officedocument")
        elif self.path.endswith('.doc'):
            self.build_headers("application/msword")
        else:
            self.build_headers()

ROBOT_STEPS = [
    {
        'step_name': "declarations",
        'check_link_func': looks_like_a_declaration_link,
        'fallback_to_selenium': False
    }
]


HTTP_SERVER = None
def start_server(host, port):
    global HTTP_SERVER
    HTTP_SERVER.serve_forever()


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
    parser.add_argument("--web-addr", dest='web_addr', required=True)
    parser.add_argument("--start-page", dest='start_page', required=True)
    parser.add_argument("--found-links-count", dest='found_links_count', type=int)
    return parser.parse_args()

def open_project(args):
    start_url = args.web_addr + THttpServer.INIT_URL_PATH
    with TRobotProject(logger, "project.txt", ROBOT_STEPS, "result", enable_search_engine=False,
                       enable_selenium=False) as project:
        project.add_office(args.web_addr)
        office_info = project.offices[0]
        office_info.create_export_folder()
        office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

        step_info = TRobotStep(office_info, ROBOT_STEPS[0])
        step_info.pages_to_process[start_url] = 0
        step_info.processed_pages = set()
        step_info.make_one_step()
        print("found {} links".format(len(step_info.step_urls)))
        if args.found_links_count is not None:
            assert args.found_links_count == len(step_info.step_urls)


if __name__ == '__main__':
    logger = setup_logging("dlrobot.log")
    args = parse_args()
    assert os.path.exists(args.start_page)
    THttpServer.INIT_PAGE_FILE_PATH = args.start_page
    TDownloadEnv.clear_cache_folder()
    TRequestPolicy.ENABLE = False
    host, port = args.web_addr.split(":")
    server_thread = threading.Thread(target=start_server, args=(host, port))
    HTTP_SERVER = http.server.HTTPServer((host, int(port)), THttpServer)
    server_thread.start()
    time.sleep(2)       # time to init sockets
    if not args.web_addr.startswith('http'):
        args.web_addr = 'http://' + args.web_addr
    try:
        open_project(args)
    finally:
        HTTP_SERVER.shutdown()
        server_thread.join(1)
        time.sleep(1)  #
