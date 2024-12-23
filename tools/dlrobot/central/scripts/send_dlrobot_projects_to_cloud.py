from common.logging_wrapper import setup_logging
import shutil
import os
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ctime", dest='max_ctime', required=False, type=int,
                        default=int(os.environ.get("CRAWL_EPOCH")),
                        help="max ctime of an input folder")
    parser.add_argument("--processed-projects-folder", dest='processed_projects_folder', required=True)
    parser.add_argument("--update-folder", dest='update_folder', required=True)
    parser.add_argument("--output-cloud-folder", dest='output_cloud_folder', required=True)
    args = parser.parse_args()
    assert args.max_ctime is not None
    return args


class TBackupper:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="backuper.log")
        assert (os.path.exists(args.output_cloud_folder))
        self.output_folder = os.path.join(args.output_cloud_folder, str(args.max_ctime))
        if not os.path.exists(self.output_folder):
            self.logger.info("create folder {}".format(self.output_folder))
            os.mkdir(self.output_folder)
        if not os.path.isdir(self.output_folder):
            shutil.move(self.output_folder, self.output_folder + ".delete_me")
            self.logger.info("create folder {}".format(self.output_folder))
            os.mkdir(self.output_folder)
            os.path.isdir(self.output_folder)

        self.logger.info("cd {}".format(args.update_folder))
        os.chdir(args.update_folder)

    def log_and_system(self, cmd):
        self.logger.info(cmd)
        exitcode = os.system(cmd)
        if exitcode != 0:
            raise Exception("Error, {} returned {}".format(cmd, exitcode))

    def create_tar_file(self, processed_projects_folder, max_ctime):
        tmp_folder = "dlrobot.{}".format(max_ctime)
        os.mkdir(tmp_folder)
        with os.scandir(processed_projects_folder) as it:
            for entry in it:
                if entry.is_dir() and entry.stat().st_ctime < max_ctime:
                    result_folder = os.path.join(processed_projects_folder, entry.name, "result")
                    self.logger.info("rm folder {} ".format(result_folder))
                    shutil.rmtree(result_folder, ignore_errors=True)

                    self.logger.info("move {} {}".format(entry.name, tmp_folder))
                    shutil.move(os.path.join(processed_projects_folder, entry.name), tmp_folder)
        tar_file = "processed_projects.tar.gz"
        self.log_and_system("tar cfz {} {}".format(tar_file, tmp_folder))

        self.logger.info("remove {}".format(tmp_folder))
        shutil.rmtree(tmp_folder, ignore_errors=True)
        return tar_file

    def copy_dlrobot_human(self):
        self.logger.info("copy dlrobot_human.dbm to {}".format(self.output_folder))
        self.log_and_system("cat dlrobot_human.dbm | gzip -c >dlrobot_human.dbm.gz")
        shutil.move("dlrobot_human.dbm.gz", self.output_folder)

    def copy_dlrobot_central_log(self):
        central_log_base_name = "dlrobot_central.log"
        central_log = os.path.join(self.args.processed_projects_folder, "..", central_log_base_name)
        self.logger.info("copy {} to {}".format(central_log, self.output_folder))
        shutil.copy2(central_log, self.output_folder)
        self.log_and_system("gzip {}".format(os.path.join(self.output_folder, central_log_base_name)))

    def move_processed_projects(self):
        tar_file = self.create_tar_file(self.args.processed_projects_folder, self.args.max_ctime)
        self.logger.info("move {} to {}".format(tar_file, self.output_folder))
        shutil.move(tar_file, self.output_folder)
        tar_file1 = os.path.join(self.output_folder, tar_file)
        list_file = os.path.join(self.output_folder, "processed_projects_file_list.txt")
        self.log_and_system("tar --file {} --list > {}".format(tar_file1, list_file))

    def main(self):
        self.logger.info("max_ctime = {}".format(self.args.max_ctime))
        self.copy_dlrobot_human()
        self.copy_dlrobot_central_log()
        self.move_processed_projects()
        self.logger.info("all done")


if __name__ == '__main__':
    TBackupper(parse_args()).main()
