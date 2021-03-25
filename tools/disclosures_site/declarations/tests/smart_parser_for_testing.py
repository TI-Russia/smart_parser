from smart_parser_http.smart_parser_server import TSmartParserHTTPServer
from smart_parser_http.smart_parser_client import TSmartParserCacheClient

import threading
import os
import time
import shutil


def start_server(server):
    server.serve_forever()


class SmartParserServerForTesting:
    SERVER_ADDRESS = "localhost:8178"

    def __init__(self, workdir, folder=None):
        self.doc_folder = folder
        self.workdir = workdir
        self.server = None

    def __enter__(self):
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        os.mkdir(self.workdir)
        server_args = [
            '--cache-file', os.path.join(self.workdir, "smart_parser.dbm"),
            '--input-task-directory', os.path.join(self.workdir, "input"),
            '--server-address', self.SERVER_ADDRESS,
            '--log-file-name', os.path.join(self.workdir, "smart_parser_server.log"),
            '--worker-count', "1"
        ]
        self.server = TSmartParserHTTPServer(TSmartParserHTTPServer.parse_args(server_args))
        os.environ['SMART_PARSER_SERVER_ADDRESS'] = self.SERVER_ADDRESS # for all clients
        self.server_thread = threading.Thread(target=start_server, args=(self.server,))
        self.server_thread.start()
        if self.doc_folder is not None:
            time.sleep(1)   # start server
            client_args = [
                '--walk-folder-recursive', self.doc_folder,
                '--action', 'put',
                '--timeout', '1'
            ]
            client = TSmartParserCacheClient(TSmartParserCacheClient.parse_args(client_args))
            client.main()
            self.server.task_queue.join()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.server is not None:
            self.server.stop_server()