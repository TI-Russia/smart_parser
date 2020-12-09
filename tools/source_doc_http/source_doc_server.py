from urllib.parse import urlparse

import hashlib
import argparse
import sys
import logging
import os
import json
import urllib
import http.server
import dbm.gnu


def setup_logging(logfilename):
    logger = logging.getLogger("source_doc_server")
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


class TSourceDocHTTPServer(http.server.HTTPServer):
    header_repeat_max_len = 20

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SOURCE_DOC_SERVER_ADDRESS")
        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="source_doc_server.log")
        parser.add_argument("--data-folder", dest='data_folder', required=False, default=".")
        parser.add_argument('--max-bin-file-size', dest='max_bin_file_size', required=False, default=10 * (2 ** 30), type=int)

        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ['SOURCE_DOC_SERVER_ADDRESS']
        return args

    def get_bin_file_path(self, i):
        return os.path.join(self.args.data_folder, "{}.bin".format(i))

    def __init__(self, args, logger=None):
        self.args = args
        self.max_bin_file_size = self.args.max_bin_file_size
        self.logger = logger if logger is not None else setup_logging(args.log_file_name)
        self.stats = None
        self.src_doc_params = None
        self.files = list()
        self.dbm_path = None
        self.load_from_disk()
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, int(port)))
        try:
            super().__init__((host, int(port)), TSourceDocRequestHandler)
        except Exception as exp:
            self.logger.error(exp)
            raise

    def load_from_disk(self):
        self.stats = {
            'bin_files_count': 1,
            'all_file_size': 0,
            'source_doc_count': 0
        }
        assert os.path.exists(self.args.data_folder)
        self.dbm_path = os.path.join(self.args.data_folder, "header.dbm")
        if os.path.exists(self.dbm_path):
            self.src_doc_params = dbm.gnu.open(self.dbm_path, "ws")
            self.stats = json.loads(self.src_doc_params.get('stats'))
        else:
            self.logger.info("create new file {}".format(self.dbm_path))
            self.src_doc_params = dbm.gnu.open(self.dbm_path, "cs")

        self.files.clear()
        for i in range(self.stats['bin_files_count'] - 1):
            fp = open(self.get_bin_file_path(i), "rb")
            assert fp is not None
            self.files.append(fp)

        fp = open(self.get_bin_file_path(self.stats['bin_files_count'] - 1), "ab+")
        assert fp is not None
        self.files.append(fp)

    def close_files(self):
        for f in self.files:
            self.logger.debug("close {}".format(f.name))
            f.close()
        self.files.clear()
        self.src_doc_params.close()

    def get_source_document(self, sha256):
        file_info = self.src_doc_params.get(sha256)
        if file_info is None:
            self.logger.debug("cannot find key {}".format(sha256))
            return None, None
        file_no, file_pos, size, extension = file_info.decode('latin').split(";")
        file_no = int(file_no)
        if file_no >= len(self.files):
            self.logger.error("bad file no {} for key ={}  ".format(file_no, sha256))
            return None, None
        self.files[file_no].seek(int(file_pos))
        file_contents = self.files[file_no].read(int(size))
        return file_contents, extension

    def create_new_bin_file(self):
        self.files[-1].close()
        self.files[-1] = open(self.get_bin_file_path(len(self.files) - 1), "rb")

        self.files.append (open(self.get_bin_file_path(len(self.files)), "ab+"))

    def write_repeat_header_to_bin_file(self, file_bytes, file_extension, output_bin_file):
        # these headers are needed if the main dbm is lost
        header_repeat = '{};{}'.format(len(file_bytes), file_extension)
        if len(header_repeat) > self.header_repeat_max_len:
            # strange long file extension can be ignored and trimmed
            header_repeat = header_repeat[:self.header_repeat_max_len]
        elif len(header_repeat) > self.header_repeat_max_len:
            header_repeat += ' ' * (self.header_repeat_max_len - len(header_repeat))
        output_bin_file.write(header_repeat.encode('latin'))

    def update_stats(self, file_bytes_len):
        self.stats['all_file_size'] += file_bytes_len + self.header_repeat_max_len
        self.stats['source_doc_count'] += 1
        self.stats['bin_files_count'] = len(self.files)
        self.src_doc_params["stats"] = json.dumps(self.stats)

    def save_source_document(self, file_bytes, file_extension):
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        if self.src_doc_params.get(sha256) is not None:
            return
        output_bin_file = self.files[-1]
        if output_bin_file.tell() > self.max_bin_file_size:
            self.create_new_bin_file()
            output_bin_file = self.files[-1]
        try:
            self.write_repeat_header_to_bin_file(file_bytes, file_extension, output_bin_file)
        except IOError as exp:
            self.logger.error("cannot write repeat header for {} to {}, exception:{}".format(
                sha256, output_bin_file.name, exp))
            raise
        try:
            start_file_pos = output_bin_file.tell()
            output_bin_file.write(file_bytes)
            output_bin_file.flush()
        except IOError as exp:
            self.logger.error("cannot write file {} (size {}) to {}, exception:{}".format(
                sha256, file_bytes, output_bin_file.name, exp))
            raise

        try:
            self.src_doc_params[sha256] = "{};{};{};{}".format(
                len(self.files) - 1,
                start_file_pos,
                len(file_bytes),
                file_extension)
        except Exception as exp:
            self.logger.error("cannot add file info {} to {}, exception:{}".format(
                sha256, self.dbm_path, exp))
            raise

        self.logger.debug("put source document {} to bin file {}".format(sha256, len(self.files) - 1 ))
        self.update_stats(len(file_bytes))

    def get_stats(self):
        return self.stats


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

    def process_get_source_document(self):
        query_components = dict()
        if not self.parse_cgi(query_components):
            self.send_error_wrapper('bad request', log_error=False)
            return

        if 'sha256' not in query_components:
            self.send_error_wrapper('sha256 not in cgi', log_error=True)
            return

        file_data, file_extension = self.server.get_source_document(query_components['sha256'])
        if file_data is None:
            self.send_error_wrapper("not found", http_code=http.HTTPStatus.NOT_FOUND, log_error=True)
            return

        self.send_response(200)
        self.send_header('file_extension', file_extension)
        self.end_headers()
        self.wfile.write(file_data)

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
            elif path == "/get_source_document":
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

