from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from common.primitives import build_dislosures_sha256

import http.client
import logging
import urllib.request
import urllib.error
import os
import json
import sys
import argparse


def setup_logging(logfilename="smart_parser_client.log"):
    logger = logging.getLogger("sc")
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


class TSmartParserCacheClient(object):

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SMART_PARSER_SERVER_ADDRESS")
        parser.add_argument("--action", dest='action', default=None, help="can be put, get, get_by_sha256 or stats", required=False)
        parser.add_argument("--walk-folder-recursive", dest='walk_folder_recursive', default=None, required=False)
        parser.add_argument("--timeout", dest='timeout', default=300, type=int)
        parser.add_argument("--rebuild", dest='rebuild', action="store_true", default=False)
        parser.add_argument('files', nargs='*')
        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ.get('SMART_PARSER_SERVER_ADDRESS')
        return args

    def assert_server_alive(self):
        if self.server_address is None:
            raise Exception("environment variable SERVER_ADDRESS is not set")

        self.logger.debug("check server {} is alive".format(self.server_address))

        try:
            with urllib.request.urlopen("http://" + self.server_address + "/ping",
                                        timeout=self.timeout) as response:
                if response.read() == "pong":
                    self.logger.debug("server {} is alive".format(self.server_address))
                    return True
        except Exception as exp:
            self.logger.error("cannot connect to {} (smart parser cache server)".format(self.server_address))
            raise

    def __init__(self, args, logger=None):
        if logger is None:
            self.logger = setup_logging()
        else:
            self.logger = logger

        self.server_address = args.server_address

        if self.server_address is None:
            self.logger.error("specify environment variable SMART_PARSER_SERVER_ADDRESS")
            assert self.server_address is not None
        self.timeout = args.timeout
        self.assert_server_alive()
        self.args = args

    def send_file(self, file_path, rebuild=False):
        conn = http.client.HTTPConnection(self.server_address)
        with open(file_path, "rb") as inp:
            file_contents = inp.read()
        self.logger.debug("send {} to smart parser cache".format(file_path))
        path = os.path.basename(file_path)
        if rebuild:
            path += "?rebuild=1"
        conn.request("PUT", path, file_contents)
        response = conn.getresponse()
        if response.code != 201:
            self.logger.error("could not put a task to smart parser cache")
            return False
        else:
            return True

    def get_stats(self):
        data = None
        try:
            conn = http.client.HTTPConnection(self.server_address)
            conn.request("GET", "/stats")
            response = conn.getresponse()
            data = response.read().decode('utf8')
            return json.loads(data)
        except Exception as exp:
            message = "conversion_client, get_stats failed: {}".format(exp)
            if data is not None:
                message += "; conversion server answer was {}".format(data)
            self.logger.error(message)
            return None

    def retrieve_json_by_sha256(self, sha256):
        conn = http.client.HTTPConnection(self.server_address)
        conn.request("GET", "/get_json?sha256=" + sha256)
        response = conn.getresponse()
        if response.code == 200:
            json_bytes = response.read()
            if json_bytes == TSmartParserHTTPServer.SMART_PARSE_FAIL_CONSTANT:
                return {}
            else:
                return json.loads(json_bytes)
        else:
            return None

    def retrieve_json_by_source_file(self, file_path):
        return self.retrieve_json_by_sha256(build_dislosures_sha256(file_path))

    def get_files(self):
        if self.args.walk_folder_recursive is not None:
            for root, dirs, files in os.walk(self.args.walk_folder_recursive):
                for filename in files:
                    _, extension = os.path.splitext(filename)
                    if extension in ACCEPTED_DOCUMENT_EXTENSIONS:
                        yield os.path.join(root, filename)
        else:
            for f in self.args.files:
                yield f

    def main(self):
        if self.args.action == "stats":
            print(json.dumps(self.get_stats()))
        else:
            for f in self.get_files():
                if self.args.action == "get_by_sha256":
                    js = self.retrieve_json_by_sha256(f)
                    if js is None:
                        print("not found")
                    else:
                        print(json.dumps(js, ensure_ascii=False))
                elif self.args.action == "get":
                    js = self.retrieve_json_by_source_file(f)
                    if js is None:
                        print("not found")
                    else:
                        print(json.dumps(js, ensure_ascii=False))
                else:
                    self.send_file(f, self.args.rebuild)


if __name__ == "__main__":
    TSmartParserCacheClient(TSmartParserCacheClient.parse_args(sys.argv[1:])).main()
