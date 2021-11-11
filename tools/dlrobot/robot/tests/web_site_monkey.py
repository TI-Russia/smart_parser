from dlrobot.robot.dl_robot import TDlrobot
from common.logging_wrapper import close_logger
from dlrobot.common.robot_project import TRobotProject
from common.download import TDownloadEnv

import shutil
import http.server
from functools import partial
from common.primitives import is_local_http_port_free
import os
import threading


def start_server(server):
    try:
        server.serve_forever()
    except Exception as exp:
        pass


class TTestEnv:

    def __init__(self, port, website_folder, regional_main_pages=[]):
        self.dlrobot = None
        self.dlrobot_project = None
        self.web_site_folder = os.path.join(os.path.dirname(__file__), website_folder)
        name = os.path.basename(website_folder)
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.{}".format(name))
        self.dlrobot_result_folder = os.path.join(self.data_folder, "result")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        handler = partial(http.server.SimpleHTTPRequestHandler,
                          directory=self.web_site_folder)
        assert is_local_http_port_free(port)
        self.web_site = http.server.HTTPServer(server_address=("127.0.0.1", port), RequestHandlerClass=handler)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)
        self.project_path = os.path.join(self.data_folder, "project.txt")
        regional = list("http://127.0.0.1:{}/{}".format(port, url) for url in regional_main_pages)

        project = TRobotProject.create_project_str("http://127.0.0.1:{}".format(port),
                                                   regional_main_pages=regional,
                                                   disable_search_engine=True)
        with open(self.project_path, "w") as outp:
            outp.write(project)

    def start_server_and_robot(self, crawling_timeout=None):
        threading.Thread(target=start_server, args=(self.web_site,)).start()
        dlrobot_args = ['--clear-cache-folder',
                        '--project', self.project_path,
                        '--selenium-timeout', '1s'
                        ]
        if crawling_timeout is not None:
            dlrobot_args.extend(['--crawling-timeout', str(crawling_timeout)])
        self.dlrobot = TDlrobot(TDlrobot.parse_args(dlrobot_args))
        self.dlrobot_project =  self.dlrobot.open_project()

    def tearDown(self):
        if self.web_site is not None:
            self.web_site.shutdown()
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
        TDownloadEnv.CONVERSION_CLIENT = None
        close_logger(self.dlrobot.logger)
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def get_result_files(self):
        files = list()
        with os.scandir(self.dlrobot_result_folder) as it1:
            for entry1 in it1:
                if entry1.is_dir():
                    with os.scandir(entry1.path) as it2:
                        for entry2 in it2:
                            if entry2.is_file():
                                files.append(entry2.path)
        return files
