import shutil
import os
import argparse
import glob
import hashlib
import logging
import tempfile



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", dest='input_glob', required=True)
    parser.add_argument("--output-folder", dest='output_folder', default="domains")
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

    def get_temp_file(self, folder, suffix):
        if self.args.use_pseudo_tmp:
            TCopier.TMP_INDEX += 1
            return os.path.join(folder, "tmp" + str(TCopier.TMP_INDEX) + suffix)
        else:
            handle, output_file = tempfile.mkstemp(dir=folder, suffix=suffix)
            os.close(handle)
            return output_file

    def copy_files_of_one_web_site(self, web_site, result_folder, output_folder):
        input_folder = os.path.join(result_folder, web_site)
        web_site_output_folder = os.path.join(output_folder, web_site)
        if not os.path.isdir(input_folder):
            self.logger.debug("ignore {}".format(input_folder))
            return

        if not os.path.exists(web_site_output_folder):
            os.mkdir(web_site_output_folder)
            for x in os.listdir(input_folder):
                input_file = os.path.join(input_folder, x)
                if os.path.isfile(input_file):
                    self.logger.debug("copy {} to {}".format(input_file, web_site_output_folder))
                    shutil.copy2(input_file, web_site_output_folder)
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
                else:
                    self.logger.debug("skip {}".format(in_sha256[sha256]))

    def copy_files(self):
        for folder in glob.glob(self.args.input_glob):
            assert os.path.isdir(folder)
            assert os.path.exists( os.path.join(folder, "dlrobot_parallel.log") )

        for folder in glob.glob(self.args.input_glob):
            for dlrobot_project in os.listdir(folder):
                project_folder = os.path.join( folder, dlrobot_project)
                if not os.path.isdir(project_folder):
                    continue
                result_folder = os.path.join(project_folder, "result")
                if not os.path.exists(result_folder):
                    self.logger.debug("no result found in {}, skip it".format(project_folder))
                    continue
                for web_site in os.listdir(result_folder):
                    self.copy_files_of_one_web_site(web_site, result_folder, self.args.output_folder)


def main():
    global PS
    copier = TCopier(parse_args())
    copier.copy_files()


if __name__ == '__main__':
    main()
