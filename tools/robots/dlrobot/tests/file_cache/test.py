import http.server
import sys
import threading
from robots.common.download import TDownloadedFile,  TDownloadEnv
import time
from robots.common.http_request import RobotHttpException
import logging
import os

HTTP_HEAD_REQUESTS_COUNT = 0
HTTP_GET_REQUESTS_COUNT = 0

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

class THttpServer(http.server.BaseHTTPRequestHandler):

    def build_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment;filename = "wrong_name.doc"')
        self.end_headers()

    def do_GET(self):
        global HTTP_GET_REQUESTS_COUNT
        HTTP_GET_REQUESTS_COUNT += 1
        logger = logging.getLogger("dlrobot_logger")
        logger.debug("GET {}".format(self.path))
        if self.path == "/somepath":
            self.build_headers()
            self.wfile.write("<html> aaaaaaa </html>".encode("latin"))
        elif self.path == "/very_long":
            time.sleep(TDownloadEnv.HTTP_TIMEOUT + 10)   # more than HTTP_TIMEOUT
            self.build_headers()
            self.wfile.write("<html> bbbb </html>".encode("latin"))
        else:
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, "not found")


    def do_HEAD(self):
        global HTTP_HEAD_REQUESTS_COUNT
        logger = logging.getLogger("dlrobot_logger")
        logger.debug("HEAD {}".format(self.path))
        HTTP_HEAD_REQUESTS_COUNT += 1
        self.build_headers()


HTTP_SERVER = None
def start_server(host, port):
    global HTTP_SERVER
    HTTP_SERVER = http.server.HTTPServer((host, int(port)), THttpServer)
    HTTP_SERVER.serve_forever()


def request_the_same(url):
    global HTTP_GET_REQUESTS_COUNT

    file1 = TDownloadedFile(url)
    assert HTTP_GET_REQUESTS_COUNT == 1
    file2 = TDownloadedFile(url)
    assert HTTP_GET_REQUESTS_COUNT == 1

def request_timeouted(url):
    got_timeout_exception = False
    try:
        TDownloadedFile(url)
    except RobotHttpException as exp:
        got_timeout_exception = True
    assert got_timeout_exception


def request_too_many_404(url):
    codes = list()
    for i in range(4):
        try:
            x = TDownloadedFile(url)
        except RobotHttpException as exp:
            codes.append(exp.http_code)
    assert codes == [404, 404, 404, 429]


if __name__ == '__main__':
    TDownloadEnv.clear_cache_folder()
    logger = setup_logging('file_cache.log')
    web_addr = sys.argv[1]
    host, port = web_addr.split(":")

    logger.debug("start http server on {}".format(web_addr))
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()

    logger.debug("request_the_same")
    request_the_same(web_addr +"/somepath")

    logger.debug("request_too_many_404")
    request_too_many_404(web_addr + "/not_existing")

    logger.debug("request_timeouted")
    request_timeouted(web_addr + "/very_long")

    logger.debug("sleep {}".format(TDownloadEnv.HTTP_TIMEOUT))
    time.sleep(TDownloadEnv.HTTP_TIMEOUT)

    logger.debug("shutdown http server")
    HTTP_SERVER.shutdown()
    server_thread.join(1)