from DeclDocRecognizer.external_convertors import TExternalConverters
from urllib.parse import urlparse
from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from common.primitives import build_dislosures_sha256_by_file_data
from common.logging_wrapper import setup_logging


from multiprocessing.pool import ThreadPool
from functools import partial
import argparse
import sys
import time
import os
import json
import urllib
import zlib
import http.server
import dbm.gnu
import threading
import queue
from pathlib import Path


class TSmartParserHTTPServer(http.server.HTTPServer):
    SMART_PARSE_FAIL_CONSTANT = b"no_json_found"
    TASK_TIMEOUT = 10

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SMART_PARSER_SERVER_ADDRESS")
        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="smart_parser_cache.log")
        parser.add_argument("--cache-file", dest='cache_file', required=False, default="smart_parser_cache.dbm")
        parser.add_argument("--input-task-directory", dest='input_task_directory',
                            required=False, default="input_tasks")
        parser.add_argument("--worker-count", dest='worker_count', default=2, type=int)
        parser.add_argument("--disk-sync-rate", dest='disk_sync_rate', default=3, type=int)
        parser.add_argument("--heart-rate", dest='heart_rate', type=int, required=False, default=600)
        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ['SMART_PARSER_SERVER_ADDRESS']
        return args

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name=self.args.log_file_name, append_mode=True)
        self.converters = TExternalConverters()
        self.json_cache_dbm = dbm.gnu.open(args.cache_file, "w" if os.path.exists(args.cache_file) else "c")
        self.last_version = self.read_smart_parser_versions()
        self.task_queue = self.initialize_input_queue()
        self.session_write_count = 0
        self.worker_pool = None
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, int(port)))
        self.working = True
        self.unsynced_records_count = 0
        self.last_heart_beat = time.time()
        try:
            super().__init__((host, int(port)), TSmartParserRequestHandler)
        except Exception as exp:
            self.logger.error(exp)
            raise
        self.logger.debug("start main smart_parser_thread")
        self.smart_parser_thread = threading.Thread(target=self.run_smart_parser_thread_pool)
        self.smart_parser_thread.start()

    def stop_server(self):
        self.json_cache_dbm.sync()
        self.json_cache_dbm.close()
        self.working = False
        self.server_close()
        time.sleep(self.TASK_TIMEOUT)
        self.worker_pool.close()
        self.smart_parser_thread.join(0)
        self.shutdown()

    def check_file_extension(self, filename):
        _, extension = os.path.splitext(filename)
        return extension in ACCEPTED_DOCUMENT_EXTENSIONS

    def initialize_input_queue(self):
        if not os.path.exists(self.args.input_task_directory):
            try:
                os.mkdir(self.args.input_task_directory)
            except Exception as exp:
                self.logger.error ("cannot create input task directory {}".format(self.args.input_task_directory))
                raise
        task_queue = queue.Queue()
        for file_name in sorted(Path(self.args.input_task_directory).iterdir(), key=os.path.getmtime):
            if self.check_file_extension(str(file_name)):
                task_queue.put(os.path.basename(file_name))
        self.logger.error("initialize input task queue with {} files".format(task_queue.qsize()))
        return task_queue

    def read_smart_parser_versions(self):
        with open (os.path.join(os.path.dirname(__file__), "../../src/Resources/versions.txt"), "r") as inp:
            versions = json.load(inp)
            last_version = versions['versions'][-1]['id']
            assert last_version is not None
            self.logger.error("last smart parser version is {}".format(last_version))
            version_in_binary = self.converters.get_smart_parser_version()
            if version_in_binary != last_version:
                self.logger.error("smart parser binary is outdated, compile it  ")
                assert version_in_binary == last_version
            return last_version

    def build_key(self, sha256, smart_parser_version):
        if smart_parser_version is None:
            smart_parser_version = self.last_version
        return ",".join([sha256, smart_parser_version])

    def get_smart_parser_json(self, sha256, smart_parser_version=None):
        key = self.build_key(sha256, smart_parser_version)
        js = self.json_cache_dbm.get(key)
        if js is None:
            self.logger.debug("cannot find key {}".format(key))
            return None
        if js == TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
            return TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT
        js = zlib.decompress(js)
        self.logger.debug("found value of length {} by key {}".format(len(js), key))
        return js

    def put_to_task_queue(self, file_bytes, file_extension, rebuild=False):
        sha256 = build_dislosures_sha256_by_file_data(file_bytes, file_extension)
        file_name = os.path.join(self.args.input_task_directory, sha256 + file_extension)
        if os.path.exists(file_name):
            self.logger.debug("file {} already exists in the input queue".format(file_name))
            return
        key = self.build_key(sha256, None)
        if not rebuild:
            if self.json_cache_dbm.get(key) is not None:
                self.logger.debug("file {} already exists in the db".format(file_name))
                return

        if not self.check_file_extension(str(file_name)):
            self.logger.debug("bad file extension  {}".format(file_name))
            return

        with open (file_name, "wb") as outp:
            outp.write(file_bytes)
        self.task_queue.put(os.path.basename(file_name))
        self.logger.debug("put {} to queue".format(file_name))

    def sync_to_disc(self, force=False):
        if self.unsynced_records_count > 0:
            if force or (self.unsynced_records_count >= self.args.disk_sync_rate):
                self.json_cache_dbm.sync()
                self.unsynced_records_count = 0
            self.logger.debug("there are {} records to be stored to disk".format(self.unsynced_records_count))

    def register_built_smart_parser_json(self, sha256, json_data):
        key = self.build_key(sha256, None)
        self.logger.debug("add json to key  {}".format(key))
        self.session_write_count += 1
        if json_data != TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
            json_data = zlib.compress(json_data)
        self.json_cache_dbm[key] = json_data
        self.unsynced_records_count += 1
        self.sync_to_disc()

    def get_tasks(self):
        while self.working:
            try:
                file_name = self.task_queue.get(True, timeout=self.TASK_TIMEOUT)
                file_path = os.path.join(self.args.input_task_directory, file_name)
                if os.path.exists(file_path):
                    yield file_path
                else:
                    self.logger.error("file {} does not exist".format(file_path))
            except queue.Empty as exp:
                pass

    def run_smart_parser(self, file_path):
        sha256, json_data = self.converters.run_smart_parser_official(
            file_path, self.logger, TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT)
        self.task_queue.task_done()
        return sha256, json_data

    def run_smart_parser_thread_pool(self):
        self.logger.debug("run smart_parser in {} threads".format(self.args.worker_count))
        self.worker_pool = ThreadPool(self.args.worker_count)
        try:
            task_results = self.worker_pool.imap_unordered(partial(self.run_smart_parser), self.get_tasks())
            for (sha256, json_data) in task_results:
                self.register_built_smart_parser_json(sha256, json_data)
        except Exception as exp:
            self.logger.error("general exception in run_smart_parser_thread: {} ".format(exp))
            raise

    def get_stats(self):
        return {
            'queue_size': self.task_queue.qsize(),
            'session_write_count': self.session_write_count,
            'unsynced_records_count': self.unsynced_records_count
        }

    def service_actions(self):
        current_time = time.time()
        if current_time - self.last_heart_beat >= self.args.heart_rate:
            self.sync_to_disc(True)
            self.last_heart_beat = time.time()


class TSmartParserRequestHandler(http.server.BaseHTTPRequestHandler):

    timeout = 10*60

    def parse_cgi(self, query_components):
        query = urllib.parse.urlparse(self.path).query
        if query == "":
            return True
        for qc in query.split("&"):
            items = qc.split("=")
            if len(items) != 2:
                return False
            query_components[items[0]] = items[1]
        return True

    def send_error_wrapper(self, message, http_code=http.HTTPStatus.BAD_REQUEST, log_error=True):
        if log_error:
            self.server.logger.error(message)
        http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)

    def process_get_json(self):
        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_wrapper('bad request', log_error=False)
            return

        if 'sha256' not in query_components:
            self.send_error_wrapper('sha256 not in cgi', log_error=True)
            return

        js = self.server.get_smart_parser_json(query_components['sha256'], query_components.get('smart_parser_version'))
        if js is None:
            self.send_error_wrapper("not found", http_code=http.HTTPStatus.NOT_FOUND, log_error=True)
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(js)
        return

    def do_GET(self):
        try:
            path = urllib.parse.urlparse(self.path).path
            if path == "/ping":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"pong\n")
            elif path == "/stats":
                self.send_response(200)
                self.end_headers()
                stats = json.dumps(self.server.get_stats()) + "\n"
                self.wfile.write(stats.encode('utf8'))
            elif path == "/get_json":
                self.process_get_json()
            else:
                self.send_error_wrapper("unsupported action", log_error=False)
        except Exception as exp:
            self.server.logger.error(exp)
            return

    def do_PUT(self):
        if self.path is None:
            self.send_error_wrapper("no file specified")
            return

        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_wrapper('bad request', log_error=False)
            return

        file_path = urllib.parse.urlparse(self.path).path
        _, file_extension = os.path.splitext(os.path.basename(file_path))

        file_length = self.headers.get('Content-Length')
        if file_length is None or not file_length.isdigit():
            self.send_error_wrapper('cannot find header  Content-Length')
            return
        file_length = int(file_length)

        self.server.logger.debug(
            "start reading file {} file size {} from {}".format(file_path, file_length, self.client_address[0]))

        try:
            file_bytes = self.rfile.read(file_length)
        except Exception as exp:
            self.send_error_wrapper('file reading failed: {}'.format(str(exp)))
            return

        try:
            if not query_components.get("external_json", False):
                self.server.put_to_task_queue(file_bytes, file_extension, ('rebuild' in query_components))
            else:
                sha256 = query_components['sha256']
                self.server.register_built_smart_parser_json(sha256, file_bytes)
        except Exception as exp:
            self.send_error_wrapper('register_task_result failed: {}'.format(str(exp)))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    server = TSmartParserHTTPServer(TSmartParserHTTPServer.parse_args(sys.argv[1:]))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        self.logger.info("ctrl+c received")
    except Exception as exp:
        self.logger.error("general exception: {}".format(exp))
    finally:
        server.smart_parser_thread.join(10)
        sys.exit(1)

