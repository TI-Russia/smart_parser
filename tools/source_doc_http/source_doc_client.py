from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from common.logging_wrapper import setup_logging

import http.client
import urllib.request
import urllib.error
import os
import json
import argparse
import sys
import socket


class TSourceDocClient(object):

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SOURCE_DOC_SERVER_ADDRESS")
        parser.add_argument("--action", dest='action', default=None, help="can be put, get or stats", required=False)
        parser.add_argument("--timeout", dest='timeout', default=300, type=int)
        parser.add_argument("--output-folder", dest='output_folder', default=".")
        parser.add_argument("--disable-first-ping", dest='enable_first_ping', action="store_false", default=True)
        parser.add_argument("--walk-folder-recursive", dest='walk_folder_recursive', default=None, required=False)
        parser.add_argument('files', nargs='*')
        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ['SOURCE_DOC_SERVER_ADDRESS']

        return args

    def assert_server_alive(self):
        self.logger.debug("check server {} is alive".format(self.server_address))
        try:
            with urllib.request.urlopen("http://" + self.server_address + "/ping",
                                        timeout=self.timeout) as response:
                if response.read() == "yes":
                    self.logger.debug("server {} is alive".format(self.server_address))
                    return True
        except Exception as exp:
            self.logger.error("cannot connect to {} (source document server)".format(self.server_address))
            raise

    def __init__(self, args, logger=None):
        self.args = args
        self.logger = logger if logger is not None else setup_logging(log_file_name="source_document_client.log", append_mode=True)
        self.server_address = args.server_address
        if self.server_address is None:
            self.logger.error("specify environment variable SOURCE_DOC_SERVER_ADDRESS")
            assert self.server_address is not None
        self.timeout = args.timeout
        if args.enable_first_ping:
            self.assert_server_alive()

    def send_file(self, file_path):
        with open(file_path, "rb") as inp:
            file_contents = inp.read()

        for try_index in range(3):
            try:
                self.logger.debug("send {} to source document server (try_index={})".format(file_path, try_index))
                conn = http.client.HTTPConnection(self.server_address, timeout=60*(try_index + 1))
                conn.request("PUT", os.path.basename(file_path), file_contents)
                response = conn.getresponse()
                if response.code != 201:
                    self.logger.error("could not put a task to smart parser cache")
                    return False
                else:
                    return True
            except socket.timeout as st:
                self.logger.error("timeout in source_doc_client.send_file")

    def get_stats(self, timeout=30):
        data = None
        try:
            conn = http.client.HTTPConnection(self.server_address, timeout=timeout)
            conn.request("GET", "/stats")
            response = conn.getresponse()
            data = response.read().decode('utf8')
            return json.loads(data)
        except Exception as exp:
            message = "get_stats failed: {}".format(exp)
            if data is not None:
                message += "; server answer was {}".format(data)
            self.logger.error(message)
            return None

    def retrieve_file_data_by_sha256(self, sha256):
        conn = http.client.HTTPConnection(self.server_address)
        conn.request("GET", "/get_source_document?sha256=" + sha256)
        response = conn.getresponse()
        if response.code == 200:
            file_extension = response.headers.get('file_extension')
            if file_extension is None:
                self.logger.error("no file extension in http headers")
                return None, None
            file_data = response.read()
            return file_data, file_extension
        else:
            return None, None


def get_files(args):
    if args.walk_folder_recursive is not None:
        for root, dirs, files in os.walk(args.walk_folder_recursive):
            for filename in files:
                _, extension = os.path.splitext(filename)
                if extension in ACCEPTED_DOCUMENT_EXTENSIONS:
                    yield os.path.join(root, filename)
    else:
        for f in args.files:
            yield f


if __name__ == "__main__":
    args = TSourceDocClient.parse_args(sys.argv[1:])
    client = TSourceDocClient(args)
    if args.action == "stats":
        print(json.dumps(client.get_stats()))
    else:
        for sha256_or_file_path in get_files(args):
            if args.action == "get":
                file_data, file_extension = client.retrieve_file_data_by_sha256(sha256_or_file_path)
                if file_data is None:
                    client.logger.error("{} not found".format(sha256_or_file_path))
                else:
                    file_path = os.path.join(args.output_folder, "{}{}".format(sha256_or_file_path, file_extension))
                    client.logger.debug("create file {}".format(file_path))
                    with open (file_path, "wb") as outp:
                        outp.write(file_data)
            else:
                client.send_file(sha256_or_file_path)

