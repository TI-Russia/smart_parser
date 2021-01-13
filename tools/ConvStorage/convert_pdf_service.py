import time
import logging
import os

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


class ConvertPdfService:
    def __init__(self):
        self.stop_requested = False
        self.logger = setup_logging()

    def stop_service(self):
        try:
            self.logger.info('HTTP_SERVER.stop_http_server() ...')
            HTTP_SERVER.stop_http_server()
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
    srv = ConvertPdfService()
    srv.run_service()

