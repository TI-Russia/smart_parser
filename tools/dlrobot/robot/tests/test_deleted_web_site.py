from dlrobot.robot.dl_robot import TDlrobot
from common.web_site_status import TWebSiteReachStatus
from dlrobot.common.robot_project import TRobotProject
from common.download import TDownloadEnv
from common.http_request import THttpRequester
from dlrobot.robot.tests.common_env import TestDlrobotEnv

import os
from unittest import TestCase


class TestDeletedWebSite(TestCase):
    def setUp(self):
        self.env = TestDlrobotEnv("data.deleted_sweb_site")

    def tearDown(self):
        self.env.delete_temp_folder()

    def test_unknown_site(self):
        self.project_path = os.path.join(self.env.data_folder, "project.txt")
        TRobotProject.create_project("http://unknown_site.org", self.project_path)
        dlrobot = TDlrobot(TDlrobot.parse_args(['--clear-cache-folder',  '--project', self.project_path]))
        try:
            project = dlrobot.open_project()
        except THttpRequester.RobotHttpException as exp:
            pass
        self.assertEqual(project.web_site_snapshots[0].reach_status, TWebSiteReachStatus.abandoned)
        TDownloadEnv.CONVERSION_CLIENT.stop_conversion_thread()
        TDownloadEnv.CONVERSION_CLIENT = None
