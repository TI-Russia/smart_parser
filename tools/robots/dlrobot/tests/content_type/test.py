import http.server
import sys
import time
import os
import threading
from robots.common.download import get_file_extension_only_by_headers, TDownloadedFile, \
             DEFAULT_HTML_EXTENSION, TDownloadEnv
from robots.common.http_request import make_http_request_urllib
import logging

HTTP_HEAD_REQUESTS_COUNT = 0
HTTP_GET_REQUESTS_COUNT = 0


class THttpServer(http.server.BaseHTTPRequestHandler):

    def build_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment;filename = "wrong_name.doc"')
        self.end_headers()

    def do_GET(self):
        global HTTP_GET_REQUESTS_COUNT
        HTTP_GET_REQUESTS_COUNT += 1
        if self.path.startswith("/redirect"):
            redirect_no = int(self.path[len("/redirect"):])
            if redirect_no < 5:
                self.send_response(301)
                self.send_header("Location", '/redirect{}'.format(redirect_no + 1))
                self.end_headers()
                return
        self.build_headers()
        self.wfile.write("<html> aaaaaaa </html>".encode("latin"))



    def do_HEAD(self):
        global HTTP_HEAD_REQUESTS_COUNT
        HTTP_HEAD_REQUESTS_COUNT += 1
        self.build_headers()


HTTP_SERVER = None
def start_server():
    global HTTP_SERVER
    HTTP_SERVER.serve_forever()


def setup_logging(logfilename="dlrobot.log"):
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


if __name__ == '__main__':
    logger = setup_logging()
    TDownloadEnv.clear_cache_folder()
    web_addr = sys.argv[1]
    host, port = web_addr.split(":")
    HTTP_SERVER = http.server.HTTPServer((host, int(port)), THttpServer)
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    time.sleep(1)
    url = web_addr +"/somepath"
    wrong_extension = get_file_extension_only_by_headers(url)
    assert wrong_extension == ".doc"   # see minvr.ru for this error
    downloaded_file = TDownloadedFile(url)
    right_extension = downloaded_file.file_extension  #read file contents to determine it's type
    assert right_extension == DEFAULT_HTML_EXTENSION
    assert HTTP_GET_REQUESTS_COUNT == 1
    assert HTTP_HEAD_REQUESTS_COUNT == 1

    # test redirects
    dummy1, dummy2, data = make_http_request_urllib(logger, web_addr + "/redirect1", "GET")
    assert data.decode('utf8').startswith("<html>")
    HTTP_SERVER.shutdown()
