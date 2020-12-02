import http.client
import logging
import urllib.request
import urllib.error
import os
import json
import argparse


def setup_logging(logfilename):
    logger = logging.getLogger("src_doc_cln")
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


class TSourceDocClient(object):

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable SOURCE_DOC_SERVER_ADDRESS")
        parser.add_argument("--action", dest='action', default=None, help="can be put, get or stats", required=False)
        parser.add_argument("--timeout", dest='timeout', default=300, type=int)
        parser.add_argument("--output-folder", dest='output_folder', default=".")
        parser.add_argument('files', nargs='*')
        args = parser.parse_args(arg_list)
        if args.server_address is None:
            args.server_address = os.environ['SOURCE_DOC_SERVER_ADDRESS']

        return args

    def assert_server_alive(self):
        if self.server_address is None:
            raise Exception("environment variable SOURCE_DOC_SERVER_ADDRESS is not set")

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
        self.logger = logger if logger is not None else setup_logging("source_document_client.log")
        self.server_address = args.server_address
        if self.server_address is None:
            self.logger.error("specify environment variable SOURCE_DOC_SERVER_ADDRESS")
            assert self.server_address is not None
        self.timeout = args.timeout
        self.assert_server_alive()

    def send_file(self, file_path):
        conn = http.client.HTTPConnection(self.server_address)
        with open(file_path, "rb") as inp:
            file_contents = inp.read()
        self.logger.debug("send {} to source document server".format(file_path))
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
            conn = http.client.HTTPConnection(self.server_address)
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


if __name__ == "__main__":
    args = TSourceDocClient.parse_args(sys.argv[1:])
    client = TSourceDocClient(args)
    if args.action == "stats":
        print(json.dumps(client.get_stats()))
    else:
        for sha256_or_file_path in args.files:
            if args.action == "get":
                file_data, file_extension = client.retrieve_file_data_by_sha256(sha256_or_file_path)
                if file_data is None:
                    client.logger.error("{} not found".format(sha256_or_file_path))
                else:
                    file_path = os.join(args.output_folder, "{}{}".format(sha256_or_file_path, file_extension))
                    client.logger.debug("create file {}".format(file_path))
                    with open (file_path, "wb") as outp:
                        outp.write(file_data)
            else:
                client.send_file(f)

