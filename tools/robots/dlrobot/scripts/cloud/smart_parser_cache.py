import argparse
import sys
import logging
import os
import json
import urllib
import zlib
import http.server
import dbm.gnu
import threading
import queue
from pathlib import Path
from DeclDocRecognizer.external_convertors import EXTERNAl_CONVERTORS
from urllib.parse import urlparse
import hashlib
from robots.common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from multiprocessing.pool import ThreadPool
from functools import partial


def setup_logging(logfilename):
    logger = logging.getLogger("spc")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", dest='server_address', default=None, help="by default read it from environment variable SMART_PARSER_SERVER_ADDRESS")
    parser.add_argument("--log-file-name",  dest='log_file_name', required=False, default="smart_parser_cache.log")
    parser.add_argument("--cache-file",  dest='cache_file', required=False, default="smart_parser_cache.dbm")
    parser.add_argument("--input-task-directory", dest='input_task_directory',
                        required=False, default="input_tasks")
    parser.add_argument("--worker-count", dest='worker_count', default=2, type=int)

    args = parser.parse_args()
    if args.server_address is None:
        args.server_address = os.environ['SMART_PARSER_SERVER_ADDRESS']
    return args


def run_smart_parser(logger, file_path):
    try:
        logger.debug("process {} with smart_parser".format(file_path))
        EXTERNAl_CONVERTORS.run_smart_parser_full(file_path)
        smart_parser_json = file_path + ".json"
        json_data = TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT
        if os.path.exists(smart_parser_json):
            with open(smart_parser_json, "rb") as inp:
                json_data = zlib.compress(inp.read())
            os.unlink(smart_parser_json)
        sha256, _ = os.path.splitext(os.path.basename(file_path))
        logger.debug("remove file {}".format(file_path))
        os.unlink(file_path)
        return sha256, json_data
    except Exception as exp:
        logger.error("Exception in run_smart_parser_thread:{}".format(exp))
        raise


class TSmartParserHTTPServer(http.server.HTTPServer):
    SMART_PARSE_FAIL_CONSTANT = b"no_json_found"

    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.json_cache_dbm = dbm.gnu.open(args.cache_file, "ws" if os.path.exists(args.cache_file) else "cs")
        self.last_version = self.read_smart_parser_versions()
        self.task_queue = self.initialize_input_queue()
        self.smart_parser_thread = threading.Thread(target=self.run_smart_parser_thread)
        self.session_write_count = 0
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, int(port)))
        try:
            super().__init__((host, int(port)), TSmartParserRequestHandler)
        except Exception as exp:
            self.logger.error(exp)
            raise

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
        for file_name in sorted(Path(args.input_task_directory).iterdir(), key=os.path.getmtime):
            if self.check_file_extension(str(file_name)):
                task_queue.put(os.path.basename(file_name))
        self.logger.error("initialize input task queue with {} files".format(task_queue.qsize()))
        return task_queue

    def read_smart_parser_versions(self):
        with open (os.path.join(os.path.dirname(__file__), "../../../../../src/Resources/versions.txt"), "r") as inp:
            versions = json.load(inp)
            last_version = versions['versions'][-1]['id']
            assert last_version is not None
            self.logger.error("last smart parser version is {}".format(last_version))
            version_in_binary = EXTERNAl_CONVERTORS.get_smart_parser_version()
            if version_in_binary != last_version:
                self.logger.error("smart parser binary is outdated, compile it  ")
                assert version_in_binary == last_version
            return last_version

    def build_key(self, sha256, smart_parser_version):
        if smart_parser_version is None:
            smart_parser_version = self.last_version
        return ",".join([sha256, smart_parser_version])

    def get_smart_parser_json(self, sha256, smart_parser_version):
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

    def put_to_task_queue(self, file_bytes, file_extension):
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        file_name = os.path.join(self.args.input_task_directory, sha256 + file_extension)
        if os.path.exists(file_name):
            self.logger.debug("file {} already exists in the input queue".format(file_name))
            return
        key = self.build_key(sha256, None)
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

    def register_built_smart_parser_json(self, sha256, json_data):
        key = self.build_key(sha256, None)
        self.logger.debug("add json to key  {}".format(key))
        self.session_write_count += 1
        # do we need here a thread lock?
        self.json_cache_dbm[key] = json_data

    def get_tasks(self):
        while True:
            file_name = self.task_queue.get()
            file_path = os.path.join(self.args.input_task_directory, file_name)
            if os.path.exists(file_path):
                yield file_path
            else:
                self.logger.error("file {} does not exist".format(file_path))

    def run_smart_parser_thread(self):
        self.logger.debug("run smart_parser in {} threads".format(self.args.worker_count))
        pool = ThreadPool(self.args.worker_count)
        try:
            task_results = pool.imap_unordered(partial(run_smart_parser, self.logger), self.get_tasks())
            for (sha256, json_data) in task_results:
                self.register_built_smart_parser_json(sha256, json_data)
        except Exception as exp:
            self.logger.error("general exception in run_smart_parser_thread: {} ".format(exp))
            raise

    def get_stats(self):
        return {
            'queue_size': self.task_queue.qsize(),
            'session_write_count': self.session_write_count
        }



HTTP_SERVER = None


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
            HTTP_SERVER.logger.error(message)
        http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)

    def process_get_json(self):
        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_wrapper('bad request', log_error=False)
            return

        if 'sha256' not in query_components:
            self.send_error_wrapper('sha256 not in cgi', log_error=True)
            return

        js = HTTP_SERVER.get_smart_parser_json(query_components['sha256'], query_components.get('smart_parser_version'))
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
                stats = json.dumps(HTTP_SERVER.get_stats()) + "\n"
                self.wfile.write(stats.encode('utf8'))
            elif path == "/get_json":
                self.process_get_json()
            else:
                self.send_error_wrapper("unsupported action", log_error=False)
        except Exception as exp:
            HTTP_SERVER.logger.error(exp)
            return


    def do_PUT(self):
        if self.path is None:
            self.send_error_wrapper("no file specified")
            return

        _, file_extension = os.path.splitext(os.path.basename(self.path))

        file_length = self.headers.get('Content-Length')
        if file_length is None or not file_length.isdigit():
            self.send_error_wrapper('cannot find header  Content-Length')
            return
        file_length = int(file_length)

        HTTP_SERVER.logger.debug(
            "start reading file {} file size {} from {}".format(self.path, file_length, self.client_address[0]))

        try:
            file_bytes = self.rfile.read(file_length)
        except Exception as exp:
            self.send_error_wrapper('file reading failed: {}'.format(str(exp)))
            return

        try:
            HTTP_SERVER.put_to_task_queue(file_bytes, file_extension)
        except Exception as exp:
            self.send_error_wrapper('register_task_result failed: {}'.format(str(exp)))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(args.log_file_name)
    HTTP_SERVER = TSmartParserHTTPServer(args, logger)
    HTTP_SERVER.logger.debug("start main smart_parser_thread")
    HTTP_SERVER.smart_parser_thread.start()
    try:
        HTTP_SERVER.serve_forever()
    except KeyboardInterrupt:
        logger.info("ctrl+c received")
    except Exception as exp:
        sys.stderr.write("general exception: {}\n".format(exp))
        logger.error("general exception: {}".format(exp))
    finally:
        HTTP_SERVER.smart_parser_thread.join(10)
        sys.exit(1)

