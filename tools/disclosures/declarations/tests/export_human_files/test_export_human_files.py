
#from django.test import SimpleTestCase
from django.test import TestCase
import os
import shutil


class JoinDLrobotAndHuman(TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(__file__))

    def run_cmd(self, cmd):
        exit_value = os.system(cmd)
        self.assertEqual(exit_value,  0)

    def test_join_dlrobot_and_human(self):
        script = "../../../scripts/export_human_files.py"
        output_json = "human_files.json"
        self.run_cmd("python {} --max-files-count 1 --table  declarations_documentfile --output-folder human_files --output-json {}".format(
            script, output_json))

        self.run_cmd("git diff {}".format(output_json))

