from dl_robot.dlrobot import TDlrobot
from web_site_db.robot_web_site import TWebSiteReachStatus
from web_site_db.robot_project import TRobotProject
from common.download import TDownloadEnv


import os
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
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(self.data_folder):
            shutil.rmtree(self.data_folder, ignore_errors=True)

    def test_unknown_site(self):
        self.project_path = os.path.join(self.data_folder, "project.txt")
        TRobotProject.create_project("http://unknown_site.org", self.project_path)
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.project_path]))
        project = dlrobot.open_project()
        self.assertEqual(project.web_site_snapshots[0].reach_status, TWebSiteReachStatus.abandoned)
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
        TDownloadEnv.CONVERSION_CLIENT = None
