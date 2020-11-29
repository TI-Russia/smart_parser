import http.server
import urllib
import os
import threading
from common.download import TDownloadEnv
from common.robot_step import TRobotStep, TUrlInfo
from common.robot_project import TRobotProject
from dlrobot.declaration_link import looks_like_a_declaration_link
from common.http_request import TRequestPolicy
import logging
import argparse
import time
#import yappi


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
    parser.add_argument("--project", dest='project', required=False, default="project.txt")
    parser.add_argument("--enable-selenium", dest='enable_selenium', required=False, default=False, action="store_true")
    return parser.parse_args()


def open_project(args):
    start_url = args.web_addr + THttpServer.INIT_URL_PATH
    with TRobotProject(logger, args.project, ROBOT_STEPS, "result", enable_search_engine=False,
                       enable_selenium=args.enable_selenium) as project:
        project.add_office(args.web_addr)
        office_info = project.offices[0]
        office_info.create_export_folder()
        office_info.url_nodes[start_url] = TUrlInfo(title="", step_name=None)

        step_info = TRobotStep(office_info, ROBOT_STEPS[0])
        step_info.pages_to_process[start_url] = 0
        step_info.processed_pages = set()
        step_info.make_one_step()
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
    ROBOT_STEPS[0]['fallback_to_selenium']  = args.enable_selenium
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
        #yappi.start()
        open_project(args)
        logger.debug("normal exit")
        #print_all(yappi.get_func_stats())
    finally:
        HTTP_SERVER.shutdown()
        server_thread.join(1)
        time.sleep(1)  #
