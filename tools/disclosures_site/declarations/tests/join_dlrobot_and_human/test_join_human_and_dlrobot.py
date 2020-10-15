
from django.test import TestCase
import os
import shutil
import time


class JoinDLrobotAndHuman(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))
        self.domains_folder = "domains"
        if os.path.exists(self.domains_folder):
            shutil.rmtree(self.domains_folder)
        self.dlrobot_human_path = "dlrobot_human.json"
        if os.path.exists(self.dlrobot_human_path):
            os.unlink(self.dlrobot_human_path)

    def run_cmd(self, cmd):
        print (cmd)
        exit_value = os.system(cmd)
        self.assertEqual(exit_value,  0)

    def test_join_dlrobot_and_human(self):
        input_folder = "processed_projects"
        script = "../../../scripts/join_human_and_dlrobot.py"
        human_files = "human_files.json"
        old_db = "old/dlrobot_human.json"
        self.run_cmd("python3 {} --max-ctime {} --input-dlrobot-folder {} --human-json {} --old-dlrobot-human-json {}"
                     " --output-domains-folder {}  --output-json {}".format(
            script,
            int(time.time()),
            input_folder,
            human_files,
            old_db,
            self.domains_folder,
            self.dlrobot_human_path))
        self.run_cmd("git diff {}".format(self.dlrobot_human_path))

