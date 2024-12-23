from common.logging_wrapper import setup_logging
from conv_storage_server import TConvertProcessor

import time
import os


WORKING_DIR = "c:\\tmp\\conv_db"
SERVER_ADDRESS = "192.168.100.152:8091" #production
#SERVER_ADDRESS="127.0.0.1:8091" #dev


class ConvertPdfService:

    def __init__(self):
        self.server = None
        self.stop_requested = False
        self.logger = setup_logging(logger_name="conv_pdf_service")

    def stop_service(self):
        try:
            if self.server is not None:
                self.logger.info('stop_http_server() ...')
                self.server.stop_http_server()
        except Exception as exp:
            self.logger.error(exp)
            raise
        self.stop_requested = True

    def run_service(self):
        self.logger.debug("chdir {}".format(WORKING_DIR))
        os.chdir(WORKING_DIR)
        server_args = TConvertProcessor.parse_args(['--server-address',  SERVER_ADDRESS,
            '--db-json', 'converted_file_storage.json',
        ])
        self.logger.debug("server_args={}".format(str(server_args)))
        self.server = TConvertProcessor(server_args)

        while True:
            if self.stop_requested:
                self.logger.info('Stopping http_server')
                self.server.stop_http_server()
                break
            try:
                self.logger.debug("start_http_server")
                self.server.start_http_server()
            except Exception as exp:
                self.logger.error("general exception: {}".format(str(exp)))
                self.server.stop_http_server()
            if not self.stop_requested:
                self.logger.info('service is restarting in 5 seconds')
                time.sleep(5)


if __name__ == '__main__':
    srv = ConvertPdfService()
    srv.run_service()

