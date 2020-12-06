from dl_robot.dlrobot import TDlrobot
from common.web_site import TWebSiteReachStatus
from common.download import TDownloadEnv

import os
import json
import shutil
from unittest import TestCase


class TestDeletedWebSite(TestCase):
    def setUp(self):
        self.data_folder = os.path.join(os.path.dirname(__file__), "data.deleted_sweb_site")
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)
        os.mkdir(self.data_folder)
        os.chdir(self.data_folder)

    def tearDown(self):
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def test_unknown_site(self):
        self.project_path = os.path.join(self.data_folder, "project.txt")
        with open(self.project_path, "w") as outp:
            project = {"sites": [{"morda_url": "http://unknown_site.org"}]}
            json.dump(project, outp)
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.project_path]))
        project = dlrobot.open_project()
        self.assertEqual( project.offices[0].reach_status, TWebSiteReachStatus.abandoned)
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
        TDownloadEnv.CONVERSION_CLIENT = None
