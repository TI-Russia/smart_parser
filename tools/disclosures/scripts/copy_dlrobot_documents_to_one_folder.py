import shutil
import os
import argparse
import glob
import hashlib
import logging
import tempfile
from robots.common.robot_project import TRobotProject
import re
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", dest='input_glob', required=True)
    parser.add_argument("--output-folder", dest='output_folder', default="domains")
    parser.add_argument("--output-json", dest='output_json', default="copy_to_one_folder.json")
    parser.add_argument("--use-pseudo-tmp", dest='use_pseudo_tmp', action="store_true", default=False)
    return parser.parse_args()


def setup_logging(logfilename):
    logger = logging.getLogger("join_logger")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    #logger.addHandler(ch)
    return logger


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


def file_to_sha256(folder):
    files = dict()
    for x in os.listdir(folder):
        path = os.path.join(folder, x)
        if os.path.isfile(path):
            files[build_sha256(path)] = path
    return files


class TCopier:
    TMP_INDEX = 0

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging("copier.log")
        if not os.path.exists(args.output_folder):
            os.mkdir(args.output_folder)
        self.file_infos = dict()

    def get_temp_file(self, folder, suffix):
        if self.args.use_pseudo_tmp:
            TCopier.TMP_INDEX += 1
            return os.path.join(folder, "tmp" + str(TCopier.TMP_INDEX) + suffix)
        else:
            handle, output_file = tempfile.mkstemp(dir=folder, suffix=suffix)
            os.close(handle)
            return output_file

    def register_file_info(self, web_site, file_path, file_info):
        if web_site not in self.file_infos:
            self.file_infos[web_site] = {}
        self.file_infos[web_site][file_path] = file_info

    def copy_files_of_one_web_site(self, web_site, file_info, result_folder, output_folder):
        input_folder = os.path.join(result_folder, web_site)
        web_site_output_folder = os.path.join(output_folder, web_site)
        if not os.path.isdir(input_folder):
            self.logger.debug("ignore {}".format(input_folder))
            return

        if not os.path.exists(web_site_output_folder):
            os.mkdir(web_site_output_folder)
            for base_name in os.listdir(input_folder):
                input_file = os.path.join(input_folder, base_name)
                if os.path.isfile(input_file):
                    self.logger.debug("copy {} to {}".format(input_file, web_site_output_folder))
                    shutil.copy2(input_file, web_site_output_folder)
                    self.register_file_info(web_site, base_name, file_info[base_name])
        else:
            in_sha256 = file_to_sha256(input_folder)
            out_sha256 = file_to_sha256(web_site_output_folder)
            for sha256 in in_sha256:
                if sha256 not in out_sha256:
                    input_file = in_sha256[sha256]
                    _, extension = os.path.splitext(input_file)
                    output_file = self.get_temp_file(web_site_output_folder, extension)
                    self.logger.debug("copy {} to {}".format(input_file, output_file))
                    shutil.copy(input_file, output_file)
                    self.register_file_info(web_site, os.path.basename(output_file), file_info[os.path.basename(input_file)])
                else:
                    self.logger.debug("skip {}".format(in_sha256[sha256]))

    def get_file_urls(self, robot_project_path):
        file_info = {}
        try:
            with TRobotProject(self.logger, robot_project_path, [], None, enable_selenium=False, enable_search_engine=False) as project:
                project.read_project(fetch_morda_url=False)
                office_info = project.offices[0]
                for export_record in office_info.export_env.exported_files:
                    url = export_record.url
                    export_path = os.path.basename(export_record.export_path )
                    file_info[export_path] = url
                return file_info
        except Exception as exp:
            self.logger.debug("Fail on {}, exception={}".format(robot_project_path, exp))

    def copy_files(self):
        for folder in glob.glob(self.args.input_glob):
            self.logger.debug ("check {}".format(folder))
            assert os.path.isdir(folder)

        for folder in glob.glob(self.args.input_glob):
            for dlrobot_project in os.listdir(folder):
                self.logger.debug("process {}".format(dlrobot_project))
                project_folder = os.path.join(folder, dlrobot_project)
                if not os.path.isdir(project_folder):
                    continue
                result_folder = os.path.join(project_folder, "result")
                if not os.path.exists(result_folder):
                    self.logger.debug("no result found in {}, skip it".format(project_folder))
                    continue
                dlrobot_project_without_timestamp = re.sub('\.15[0-9]+$', '', dlrobot_project)
                robot_project = os.path.join(project_folder, dlrobot_project_without_timestamp + ".txt")
                file_info = self.get_file_urls(robot_project)
                if file_info is not None:
                    for web_site in os.listdir(result_folder):
                        self.copy_files_of_one_web_site(web_site, file_info, result_folder, self.args.output_folder)


def main():
    copier = TCopier(parse_args())
    copier.copy_files()
    with open(copier.args.output_json, "w", encoding="utf8") as outf:
        json.dump(copier.file_infos, outf, indent=4)


if __name__ == '__main__':
    main()
