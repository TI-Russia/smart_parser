import http.client
import logging
import urllib.request
import urllib.error
import hashlib
import os
import json
import argparse


class TSmartParserCacheClient(object):
    SERVER_ADDRESS = os.environ.get('SMART_PARSER_SERVER_ADDRESS')

    def __init__(self, logger):
        if TSmartParserCacheClient.SERVER_ADDRESS is None:
            logger.error("specify environment variable SMART_PARSER_SERVER_ADDRESS")
            assert TSmartParserCacheClient.SERVER_ADDRESS is not None
        assert_server_alive()
        self.db_conv_url = TSmartParserCacheClient.SERVER_ADDRESS
        self.logger = logger

    def send_file(self, file_path):
        conn = http.client.HTTPConnection(self.db_conv_url)
        with open(file_path, "rb") as inp:
            file_contents = inp.read()
        self.logger.debug("send {} to smart parser cache".format(file_path))
        conn.request("PUT", os.path.basename(file_path), file_contents)
        response = conn.getresponse()
        if response.code != 201:
            self.logger.error("could not put a task to smart parser cache")
            return False
        else:
            return True

    def get_stats(self):
        data = None
        try:
            conn = http.client.HTTPConnection(self.db_conv_url)
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

    def retrieve_json_by_source_file(self, file_path):
        with open(f, "rb") as inp:
            sha256 = hashlib.sha256(inp.read()).hexdigest()

        conn = http.client.HTTPConnection(self.db_conv_url)
        conn.request("GET", "/get_json?sha256=" + sha256)
        response = conn.getresponse()
        if response.code == 200:
            return json.loads(response.read())
        else:
            return None


def assert_server_alive():
    if TSmartParserCacheClient.SERVER_ADDRESS is None:
        raise Exception("environment variable SERVER_ADDRESS is not set")

    try:
        with urllib.request.urlopen("http://" + TSmartParserCacheClient.SERVER_ADDRESS + "/ping", timeout=300) as response:
            if response.read() == "yes":
                return True
    except Exception as exp:
        print("cannot connect to {} (smart parser cache server)".format(TSmartParserCacheClient.SERVER_ADDRESS))
        raise


def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_parallel")
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
    parser.add_argument("--action", dest='action', default=None, help="can be put, get or stats", required=True)
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging("smart_parser_cache_client.log")
    client = TSmartParserCacheClient(logger)
    if args.action == "stats":
        print(json.dumps(client.get_stats()))
    else:
        for f in args.files:
            if args.action == "get":
                js = client.retrieve_json_by_source_file(f)
                if js is None:
                    print("not found")
                else:
                    print(json.dumps(js, ensure_ascii=False))
            else:
                client.send_file(f)

