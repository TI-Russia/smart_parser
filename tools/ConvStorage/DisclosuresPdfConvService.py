import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import logging
import os
from conv_storage_server import conversion_server_main, parse_args, HTTP_SERVER

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


class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "DisclosuresPdfConvService"
    _svc_display_name_ = "Disclosures Pdf Conversion Service"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.stop_requested = False
        self.logger = setup_logging()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.logger.info('Stopping service ...')
        win32event.SetEvent(self.hWaitStop)
        try:
            self.logger.info('HTTP_SERVER.stop_http_server() ...')
            HTTP_SERVER.stop_http_server()
        except Exception as exp:
            self.logger.error(exp)
            raise
        self.stop_requested = True

    def SvcDoRun(self):
        self.logger.info('start')
        try:
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, ''))
        except Exception as exp:
            self.logger.error(exp)
            raise
        self.logger.info('run main')
        self.main()

    def main(self):
        self.logger.debug("chdir {}".format(WORKING_DIR))
        os.chdir(WORKING_DIR)
        sys.argv = ['conv_storage_server.py',
            '--server-address',  SERVER_ADDRESS,
            '--db-json', 'converted_file_storage.json',
        ]
        args = parse_args()
        self.logger.debug("args={}".format(str(args)))
        while True:
            if self.stop_requested:
                self.logger.info('Stopping HTTP_SERVER {}'.format(HTTP_SERVER))
                HTTP_SERVER.stop_http_server()
                break
            try:
                conversion_server_main(args)
            except Exception as exp:
                self.logger.error("general exception: {}".format(str(exp)))
                HTTP_SERVER.stop_http_server()
                raise
            if not self.stop_requested:
                self.logger.info('service is restarting in 5 seconds')
                time.sleep(5)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AppServerSvc)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AppServerSvc)
