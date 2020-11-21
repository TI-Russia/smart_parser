import os

TEST_FILES = [
  "assignments_test_minkult_01_stable_09-01-2020.tsv",
  "assignments_test_pool_01_08-04-2019.tsv",
  "assignments_test_pool_02_08-04-2019.tsv",
  "assignments_test_pool_03_26-04-2019.tsv",
  "assignments_test_pool_04_08-04-2019.tsv",
  "assignments_test_pool_05_13-04-2019.tsv",
  "assignments_test_pool_06_13-04-2019.tsv",
  "assignments_test_pool_07_13-04-2019.tsv",
  "assignments_test_pool_08_08-12-2019.tsv",
]

TRAIN_FILES = [
  "assignments_train_pool_01_14-04-2019.tsv",
  "assignments_train_pool_02_14-04-2019.tsv",
  "assignments_train_pool_03_22-04-2019.tsv",
  "assignments_train_pool_04_22-04-2019.tsv",
  "assignments_train_minkult_01_10-01-2020.tsv",
]

DJANGO_ROOT = os.path.join(os.path.dirname(__file__), "../..")
class TConversion:
    def __init__(self):
        self.output_assignment_folder = "../assignments"
        # for converted assignment pools
        if not os.path.exists(self.output_assignment_folder):
            os.mkdir(self.output_assignment_folder)
        self.declarator_path =  os.path.expanduser("~/declarator/transparency")
        self.manage_script = '../../manage.py'

    def convert_pools(self, pools):
        input_pools = " ".join(os.path.join(c.declarator_path, "toloka/assignments", p) for p in pools)
        cmd = "python3 {} import_declarator_toloka_pool --output-folder {} --settings disclosures.settings.prod \
            --input-pools {} ".format(self.manage_script, self.output_assignment_folder, input_pools)
        print(cmd)
        if os.system(cmd) != 0:
            exit(1)

    def make_pool(self, input_files, output_pool):
        script = os.path.join(self.declarator_path, "scripts/toloka_stats.py")
        cmd = "python3 {} --input-folder {}  -m {} {}".format(
            script,
            self.output_assignment_folder,
            output_pool,
            " ".join(input_files)
        )
        print(cmd)
        if os.system(cmd) != 0:
            exit(1)

    def prepare_db_squeeze(self):
        cmd = 'python3 {} import_declarator_toloka_pool --action prepare --settings disclosures.settings.prod'.format(
            self.manage_script)
        print (cmd)
        if os.system(cmd) != 0:
            exit(1)


if __name__ == '__main__':
    c = TConversion()
    pools = TEST_FILES + TRAIN_FILES
    c.prepare_db_squeeze()
    c.convert_pools(pools)
    c.make_pool(TEST_FILES, "test_pool_m.tsv")
    c.make_pool(TRAIN_FILES, "train_pool_m.tsv")
