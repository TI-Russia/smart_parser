from common.download import TDownloadedFile, TDownloadEnv
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging
from dlrobot.robot.tests.common_env import TestDlrobotEnv

import http.server
from unittest import TestCase
import time
import threading


HTTP_HEAD_REQUESTS_COUNT = 0
HTTP_GET_REQUESTS_COUNT = 0


class THttpServerHandler(http.server.BaseHTTPRequestHandler):

    def build_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment;filename = "wrong_name.doc"')
        self.end_headers()

    def do_GET(self):
        global HTTP_GET_REQUESTS_COUNT
        HTTP_GET_REQUESTS_COUNT += 1
        THttpRequester.logger.debug("GET {}".format(self.path))
        if self.path == "/somepath":
            self.build_headers()
            self.wfile.write("<html> aaaaaaa </html>".encode("latin"))
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
    web_site_port = 8198

    def build_url(self, path):
        return 'http://127.0.0.1:{}{}'.format(self.web_site_port, path)

    def setUp(self):
        self.server_address = '127.0.0.1:{}'.format(self.web_site_port)
        self.web_server = TestHTTPServer(self.web_site_port)
        threading.Thread(target=start_server, args=(self.web_server,)).start()
        time.sleep(1)
        self.env = TestDlrobotEnv("data.file_cache")

        TDownloadEnv.clear_cache_folder()
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        self.web_server.shutdown()
        close_logger(self.logger)
        self.env.delete_temp_folder()

    def test_request_the_same(self):
        url = self.build_url('/somepath')
        TDownloadedFile(url)
        self.assertEqual(HTTP_GET_REQUESTS_COUNT, 1)
        TDownloadedFile(url)
        self.assertEqual(HTTP_GET_REQUESTS_COUNT, 1)

    # cannot test it with other tests because
    def test_request_too_many_404(self):
        THttpRequester.ENABLE = True
        url = self.build_url('/request_too_many_404')
        codes = list()
        for i in range(4):
            try:
                x = TDownloadedFile(url)
            except THttpRequester.RobotHttpException as exp:
                codes.append(exp.http_code)

        canon_result = [404, 404, 404, 429]
        if codes != canon_result:
            print("test_request_too_many_404 is going to fail")
            print("THttpRequester.ALL_HTTP_REQUEST={}".format(str(THttpRequester.ALL_HTTP_REQUEST)))
        self.assertSequenceEqual(canon_result, codes)
