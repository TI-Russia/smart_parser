from common.download import TDownloadedFile, TDownloadEnv
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv


import http.server
import time
import threading
from unittest import TestCase

HTTP_HEAD_REQUESTS_COUNT = 0
HTTP_GET_REQUESTS_COUNT = 0


class THttpServerHandler(http.server.BaseHTTPRequestHandler):

    def build_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        global HTTP_GET_REQUESTS_COUNT
        HTTP_GET_REQUESTS_COUNT += 1
        THttpRequester.logger.debug("GET {}".format(self.path))
        if self.path == "/very_long":
            time.sleep(THttpRequester.DEFAULT_HTTP_TIMEOUT + 10)   # more than DEFAULT_HTTP_TIMEOUT
            self.build_headers()
            try:
                self.wfile.write("<html> bbbb </html>".encode("latin"))
            except Exception as exp:
                pass
        else:
            http.server.SimpleHTTPRequestHandler.send_error(self, 404, "not found")

    def do_HEAD(self):
        global HTTP_HEAD_REQUESTS_COUNT
        THttpRequester.logger.debug("HEAD {}".format(self.path))
        HTTP_HEAD_REQUESTS_COUNT += 1
        self.build_headers()


def start_server(server):
    server.serve_forever()


class TestHTTPServer(http.server.HTTPServer):
    def __init__(self, port):
        self.test_file_path = None
        super().__init__(('127.0.0.1', int(port)), THttpServerHandler)


class TestFileCache(TestCase):
    web_site_port = 8189

    def build_url(self, path):
        return 'http://127.0.0.1:{}{}'.format(self.web_site_port, path)

    def setUp(self):
        self.server_address = '127.0.0.1:{}'.format(self.web_site_port)
        self.web_server = TestHTTPServer(self.web_site_port)
        threading.Thread(target=start_server, args=(self.web_server,)).start()
        time.sleep(1)
        self.env = TestDlrobotEnv("data.timeout")
        TDownloadEnv.clear_cache_folder()
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        self.web_server.shutdown()
        close_logger(self.logger)
        self.env.delete_temp_folder()

    def test_request_timed_out(self):
        url = self.build_url('/very_long')
        got_timeout_exception = False
        try:
            TDownloadedFile(url)
        except THttpRequester.RobotHttpException as exp:
            got_timeout_exception = True
        except Exception as exp:
            assert False
        self.assertTrue(got_timeout_exception)
