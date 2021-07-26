from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from common.primitives import build_dislosures_sha256, normalize_whitespace
from common.logging_wrapper import setup_logging

import http.client
import urllib.request
import urllib.error
import os
import json
import sys
import argparse


class TSmartParserCacheClient(object):

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SMART_PARSER_SERVER_ADDRESS")
        parser.add_argument("--action", dest='action',
                            help="can be put, get, get_by_sha256, title, office_strings,  put_json or stats", required=False)
        parser.add_argument("--walk-folder-recursive", dest='walk_folder_recursive', default=None, required=False)
        parser.add_argument("--timeout", dest='timeout', default=300, type=int)
        parser.add_argument("--rebuild", dest='rebuild', action="store_true", default=False)
        parser.add_argument("--sha256-list", dest='sha_256_list')
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
            self.logger = setup_logging(log_file_name="smart_parser_client.log", append_mode=True)
        else:
            self.logger = logger

        self.server_address = args.server_address

        if self.server_address is None:
            self.logger.error("specify environment variable SMART_PARSER_SERVER_ADDRESS")
            assert self.server_address is not None
        self.timeout = args.timeout
        self.assert_server_alive()
        self.args = args

    def send_file(self, file_path, rebuild=False, external_json=False, smart_parser_version=None):
        conn = http.client.HTTPConnection(self.server_address)
        with open(file_path, "rb") as inp:
            file_contents = inp.read()
        self.logger.debug("send {} to smart parser cache".format(file_path))
        path = os.path.basename(file_path)
        if rebuild:
            path += "?rebuild=1"
        if external_json:
            sha256 = os.path.basename(file_path)
            sha256 = sha256[0:sha256.find('.')] # remember double file extension .docx.json
            assert len(sha256) == 64
            path += "?external_json=1&sha256=" + sha256
            if smart_parser_version is not None:
                path += "&smart_parser_version=" + smart_parser_version
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
        elif self.args.sha_256_list is not None:
            with open(self.args.sha_256_list, "r") as inp:
                for x in inp:
                    yield x.strip()
        else:
            for f in self.args.files:
                yield f

    @staticmethod
    def get_title_from_smart_parser_json(js):
        default_value = "null"
        if js is None:
            return default_value
        else:
            props = js.get('document_sheet_props', [])
            if len(props) < 1:
                return default_value
            return normalize_whitespace(props[0].get('sheet_title', default_value))

    @staticmethod
    def get_office_strings(js):
        rec = {
            'title': "",
            'roles': [],
            'departments': []
        }
        if js is None:
            return rec

        props = js.get('document_sheet_props', [])
        if len(props) > 0 and props[0].get('sheet_title') is not None:
            rec['title'] = normalize_whitespace(props[0]['sheet_title'])
        roles = set()
        departments = set()
        for p in js.get('persons', []):
            role = p.get('person', {}).get('role')
            if role is not None and len(role) > 0 and len(roles) < 10:
                roles.add(normalize_whitespace(role))
            department = p.get('person', {}).get('department')
            if department is not None and len(department) > 0 and len(departments) < 10:
                departments.add(normalize_whitespace(department))
        rec['roles'] = list(roles)
        rec['departments'] = list(departments)
        return rec

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
                elif self.args.action == "title":
                    js = self.retrieve_json_by_sha256(f)
                    title = TSmartParserCacheClient.get_title_from_smart_parser_json(js)
                    print (title)
                elif self.args.action == "office_strings":
                    js = self.retrieve_json_by_sha256(f)
                    of_strings = TSmartParserCacheClient.get_office_strings(js)
                    print(json.dumps(of_strings, ensure_ascii=False))
                elif self.args.action == "get":
                    js = self.retrieve_json_by_source_file(f)
                    if js is None:
                        print("not found")
                    else:
                        print(json.dumps(js, ensure_ascii=False))
                elif self.args.action == "put_json":
                    self.send_file(f, False, True)
                else:
                    self.send_file(f, self.args.rebuild)


if __name__ == "__main__":
    TSmartParserCacheClient(TSmartParserCacheClient.parse_args(sys.argv[1:])).main()
