from source_doc_http.source_doc_server import TSourceDocHTTPServer

import threading
import os
import time
import shutil


def start_server(server):
    server.serve_forever()


class SourceDocServerForTesting:
    SERVER_ADDRESS = "localhost:8179"

    def __init__(self, workdir):
        self.server = None
        self.workdir = workdir


    def __enter__(self):
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        os.mkdir(self.workdir)
        server_args = [
            '--data-folder', self.workdir,
            '--server-address', self.SERVER_ADDRESS,
        ]
        self.server = TSourceDocHTTPServer(TSourceDocHTTPServer.parse_args(server_args))
        os.environ["SOURCE_DOC_SERVER_ADDRESS"] = self.SERVER_ADDRESS
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()
        time.sleep(1)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.server is not None:
            self.server.stop_server()