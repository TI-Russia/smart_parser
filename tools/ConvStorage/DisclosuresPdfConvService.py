import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
from convert_pdf_service import ConvertPdfService


class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "DisclosuresPdfConvService"
    _svc_display_name_ = "Disclosures Pdf Conversion Service"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.stop_requested = False
        self.service = ConvertPdfService()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.service.stop_service()

    def SvcDoRun(self):
        self.service.logger.debug("start service")
        try:
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, ''))
        except Exception as exp:
            self.service.logger.error(exp)
            raise
        self.run_service()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AppServerSvc)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AppServerSvc)
