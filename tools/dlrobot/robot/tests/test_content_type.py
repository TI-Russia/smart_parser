from common.download import get_file_extension_only_by_headers, TDownloadedFile, \
             DEFAULT_HTML_EXTENSION, TDownloadEnv
from common.http_request import THttpRequester
from common.logging_wrapper import close_logger, setup_logging

import http.server
from unittest import TestCase
import time
import os
import threading
import shutil

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


def start_server(server):
    server.serve_forever()


class TestContentType(TestCase):
    web_site_port = 8194

    def setUp(self):
        self.server_address = '127.0.0.1:{}'.format(self.web_site_port)
        self.web_server = http.server.HTTPServer(('127.0.0.1', self.web_site_port), THttpServerHandler)
        threading.Thread(target=start_server, args=(self.web_server,)).start()
        time.sleep(1)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.content_type")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=False)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        TDownloadEnv.clear_cache_folder()
        self.logger = setup_logging(log_file_name="dlrobot.log")
        THttpRequester.initialize(self.logger)

    def tearDown(self):
        self.web_server.shutdown()
        close_logger(self.logger)
        time.sleep(1)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=False)

    def build_url(self, path):
        return 'http://' + os.path.join(self.server_address, path).replace('\\', '/')

    def test_content_type(self):
        url = self.build_url("somepath")
        wrong_extension = get_file_extension_only_by_headers(url)
        self.assertEqual(wrong_extension, ".doc")  # see minvr.ru for this error
        downloaded_file = TDownloadedFile(url)
        right_extension = downloaded_file.file_extension  # read file contents to determine it's type
        self.assertEqual(right_extension, DEFAULT_HTML_EXTENSION)
        self.assertEqual(HTTP_GET_REQUESTS_COUNT, 1)
        self.assertEqual(HTTP_HEAD_REQUESTS_COUNT, 1)

    def test_redirects(self):
        dummy1, dummy2, data = THttpRequester.make_http_request_urllib(self.build_url("redirect1"), "GET", 10)
        self.assertEqual(data.decode('utf8').startswith("<html>"), True)

