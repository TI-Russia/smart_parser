import socket
import time
import sys
import logging
import os
import argparse

from conv_storage_server import conversion_server_main, TConvertProcessor, HTTP_SERVER

WORKING_DIR = "c:\\tmp\\conv_db"
SERVER_ADDRESS = "192.168.100.152:8091" #production
#SERVER_ADDRESS="127.0.0.1:8091" #dev


def setup_logging():
    logger = logging.getLogger("conv_pdf_service")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logfilename = os.path.join(WORKING_DIR, "service.log")
    if os.path.exists(logfilename):
        os.remove(logfilename)
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action')


class AppServerSvc:
    def __init__(self, args):
        self.stop_requested = False
        self.logger = setup_logging()
        self.args = args

    def main(self):
        self.logger.debug("chdir {}".format(WORKING_DIR))
        os.chdir(WORKING_DIR)
        server_args = TConvertProcessor.parse_args(['--server-address',  SERVER_ADDRESS,
            '--db-json', 'converted_file_storage.json',
        ])
        self.logger.debug("server_args={}".format(str(server_args)))
        while True:
            if self.stop_requested:
                self.logger.info('Stopping HTTP_SERVER {}'.format(HTTP_SERVER))
                HTTP_SERVER.stop_http_server()
                break
            try:
                self.logger.debug("conversion_server_main")
                conversion_server_main(server_args)
            except Exception as exp:
                self.logger.error("general exception: {}".format(str(exp)))
                HTTP_SERVER.stop_http_server()
            if not self.stop_requested:
                self.logger.info('service is restarting in 5 seconds')
                time.sleep(5)


if __name__ == '__main__':
    args = parse_args()
    srv = AppServerSvc(args)
    srv.main()

