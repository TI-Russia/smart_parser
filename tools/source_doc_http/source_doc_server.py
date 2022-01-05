from common.file_storage import TFileStorage
from common.logging_wrapper import setup_logging

from urllib.parse import urlparse
import argparse
import sys
import os
import json
import urllib
import http.server
import time


class TSourceDocHTTPServer(http.server.HTTPServer):
    stop_file = ".stop"

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SOURCE_DOC_SERVER_ADDRESS")
        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="source_doc_server.log")
        parser.add_argument("--data-folder", dest='data_folder', required=False, default=".")

        parser.add_argument("--archive-folder", dest='archive_folder', required=False)
        parser.add_argument("--header-archive-copy-timeout", dest='header_archive_copy_timeout', required=False, type=int)

        parser.add_argument('--max-bin-file-size', dest='max_bin_file_size', required=False, default=10 * (2 ** 30), type=int)
        parser.add_argument('--read-only', dest='read_only', required=False, default=False, action="store_true")
        parser.add_argument("--heart-rate", dest='heart_rate', type=int, required=False, default=20)

        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ['SOURCE_DOC_SERVER_ADDRESS']
        if args.archive_folder is not None and args.header_archive_copy_timeout is None:
            args.header_archive_copy_timeout = 3 * 60 * 60
        return args

    def __init__(self, args, logger=None):
        self.args = args
        self.max_bin_file_size = self.args.max_bin_file_size
        self.logger = logger if logger is not None else setup_logging(log_file_name=args.log_file_name, append_mode=True)
        self.file_storage = TFileStorage(self.logger, self.args.data_folder, self.max_bin_file_size,
                                         read_only=self.args.read_only, archive_folder=self.args.archive_folder,
                                         header_archive_timeout=self.args.header_archive_copy_timeout)
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, int(port)))
        self.last_heart_beat = time.time()
        if os.path.exists(TSourceDocHTTPServer.stop_file):
            os.unlink(TSourceDocHTTPServer.stop_file)
        try:
            super().__init__((host, int(port)), TSourceDocRequestHandler)
        except Exception as exp:
            self.logger.error(exp)
            raise

    def stop_server(self):
        self.file_storage.close_file_storage()
        self.logger.info("shutdown")
        self.shutdown()
        self.server_close()
        self.logger.info("exit from def stop_server")

    def get_source_document(self, sha256):
        return self.file_storage.get_saved_file(sha256)

    def save_source_document(self, file_bytes, file_extension):
        return self.file_storage.save_file(file_bytes, file_extension)

    def get_stats(self):
        return self.file_storage.get_stats()

    def service_actions(self):
        current_time = time.time()
        if current_time - self.last_heart_beat >= self.args.heart_rate:
            if os.path.exists(TSourceDocHTTPServer.stop_file):
                os.unlink(TSourceDocHTTPServer.stop_file)
                #self.logger.info("stop_server")
                #self.stop_server()
                raise Exception("stop_server")
            self.last_heart_beat = time.time()


class TSourceDocRequestHandler(http.server.BaseHTTPRequestHandler):

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

    def process_special_commands(self):
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong\n")
        elif self.path == "/stats":
            self.send_response(200)
            self.end_headers()
            stats = json.dumps(self.server.get_stats()) + "\n"
            self.wfile.write(stats.encode('utf8'))
        else:
            return False
        return True

    def process_get_source_document(self):
        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_wrapper('bad request', log_error=False)
            return

        try:
            if self.process_special_commands():
                return
        except Exception as exp:
            self.server.logger.error(exp)
            return


        if 'sha256' not in query_components:
            self.send_error_wrapper('sha256 not in cgi', log_error=True)
            return

        file_info = self.server.get_source_document(query_components['sha256'])
        if file_info is None:
            self.send_error_wrapper("not found", http_code=http.HTTPStatus.NOT_FOUND, log_error=True)
            return

        self.send_response(200)
        self.send_header('file_extension', file_info.file_extension)
        self.end_headers()
        self.wfile.write(file_info.file_contents)

    def do_GET(self):
        try:
            try:
                if self.process_special_commands():
                    return
            except Exception as exp:
                self.server.logger.error(exp)
                return
            path = urllib.parse.urlparse(self.path).path
            if path == "/get_source_document":
                self.process_get_source_document()
            else:
                self.send_error_wrapper("unsupported action", log_error=False)
        except Exception as exp:
            self.server.logger.error(exp)
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

        self.server.logger.debug(
            "start reading file {} file size {} from {}".format(self.path, file_length, self.client_address[0]))

        try:
            file_bytes = self.rfile.read(file_length)
        except Exception as exp:
            self.send_error_wrapper('file reading failed: {}'.format(str(exp)))
            return

        try:
            self.server.save_source_document(file_bytes, file_extension)
        except Exception as exp:
            self.send_error_wrapper('writing failed: {}'.format(str(exp)))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    args = TSourceDocHTTPServer.parse_args(sys.argv[1:])
    server = TSourceDocHTTPServer(args)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.logger.info("ctrl+c received")
    except Exception as exp:
        server.logger.error("general exception: {}".format(exp))
    finally:
        sys.exit(1)

