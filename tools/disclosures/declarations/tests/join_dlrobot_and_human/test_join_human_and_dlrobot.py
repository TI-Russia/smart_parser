
from django.test import SimpleTestCase
import os
import shutil


class JoinDLrobotAndHuman(SimpleTestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))
        self.domains_folder = "domains"
        if os.path.exists(self.domains_folder):
            shutil.rmtree(self.domains_folder)
        self.dlrobot_human_path = "dlrobot_human.json"
        if os.path.exists(self.dlrobot_human_path):
            os.unlink(self.dlrobot_human_path)

    def run_cmd(self, cmd):
        exit_value = os.system(cmd)
        self.assertEqual(exit_value,  0)

    def test_join_dlrobot_and_human(self):
        script = "../../../scripts/copy_dlrobot_documents_to_one_folder.py"
        input_folder = "processed_projects"
        self.run_cmd("python {} --input-glob  {} --output-folder {} --use-pseudo-tmp".format(
            script, input_folder, self.domains_folder))

        script = "../../../scripts/join_human_and_dlrobot.py"
        human_files = "human_files.json"
        old_json = "old/dlrobot_human.json"
        self.run_cmd("python {} --dlrobot-folder {} --human-json {} --old-dlrobot-human-json {} --output-json {}".format(
            script,  self.domains_folder, human_files, old_json, self.dlrobot_human_path))
        self.run_cmd("git diff {}".format(self.dlrobot_human_path))

