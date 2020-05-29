import shutil
import os
import argparse
import glob
import json
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", dest='input_glob', required=True)
    parser.add_argument("--only-copy", dest='only_copy', required=False, default=False, action="store_true")
    parser.add_argument("--output-folder", dest='output_folder', default="domains")
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
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


class TMover:
    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.logger.info("load {}".format(args.human_json))
        with open(args.human_json, "r") as inp:
            self.human_json = json.load(inp)
        self.dlrobot_human_json = dict() #result
        self.found_by_dlrobot = set()

    def process_domain(self, domain):
        self.logger.debug("process {}".format(domain))
        domain_folder = os.path.join(self.args.dlrobot_folder, domain)
        if not os.path.isdir(domain_folder):
            return
        domain_info = dict()
        new_files_found_by_dlrobot = 0
        files_count = 0
        for file_path in os.listdir(domain_folder):
            file_path = os.path.join(domain_folder, f)
            if file_path.endswith(".json") or file_path.endswith(".txt"):
                continue
            files_count += 1
            sha256 = build_sha256(file_path)
            if sha256 in domain_info:
                self.logger.error("a file copy found: {}, ignore it".format(f)))
                continue
            file_info = {
                dhjs.dlrobot_path: file_path
            }
            human_file_info = self.human_json[dhjs.file_collection].get(sha256)
            if human_file_info is not None:
                file_info[dhjs.intersection_status] = dhjs.both_found
                file_info.update (human_file_info)
                self.found_by_dlrobot.add(sha256)
            else:
                file_info[dhjs.intersection_status] = dhjs.only_dlrobot
                new_files_found_by_dlrobot += 1
            domain_info[sha256] = file_info

        self.dlrobot_human_json[domain] = domain_info
        self.logger.debug("files: {},  new_files_found_by_dlrobot: {}".format(files_count, new_files_found_by_dlrobot))

    def copy_human_file(self, sha256, file_info):
        web_site = file_info[dhjs.declarator_web_domain]
        if web_site == "":
            web_site = "unknown_domain"
        folder = os.path.join(args.dlrobot_folder, web_site)
        if not os.path.exists(folder):
            self.logger.debug("create folder for domain {}".format(folder))
            os.mkdir(folder)
        infile = os.path.join(self.human_json[dhjs.declarator_folder], file_info[dhjs.declarator_file_path])
        outfile = os.path.join(folder, "h" + os.path.basename(infile))
        if args.skip_existing and os.path.exists(outfile):
            self.logger.debug("skip copy {}, it exists".format(outfile))
        else:
            self.logger.debug("copy {} to {}".format(binfile, outfile))
            if not os.path.exists(infile):
                self.logger.error("Error! Cannot copy {}".format(infile))
            else:

                shutil.copyfile(infile, outfile)
            file_info[dhjs.dlrobot_path] = os.path.basename(outfile)
            file_info[dhjs.intersection_status] = dhjs.only_human
        if web_site not in self.dlrobot_human_json:
            self.dlrobot_human_json[web_site] = dict()
        self.dlrobot_human_json.get(web_site][sha256] = file_info


    def move_files(self):
        for folder in glob.glob(self.args.input_glob):
            assert os.path.isdir(folder)
            assert os,path.join(folder, "dlrobot_parallel.log")

        for folder in glob.glob(self.args.input_glob):
            for dlrobot_project in os.listdir(folder):
                project_folder = os.path.join( folder, dlrobot_project)
                if not os.path.isdir(project_folder):
                    continue
                result_folder = os.path.join(project_folder, "result")
                if not os.path.exists(result_folder):
                    continue
                for web_site in os.listdir(result_folder):
                    input_folder = os.path.join(result_folder, web_site)
                    output_folder = os.path.join( self.args.output_folder, web_site)
                    if not os.path.exists(output_folder):
                        if args.only_copy:
                            shutil.copy (input_folder, self.args.output_folder)
                        else:
                            shutil.move(input_folder, self.args.output_folder)
                    else:
                        files_count = os.listdir(output_folder)



def main(args):
    logger = setup_logging("mover.log")
    joiner = TMover(args, logger)
    joiner.move_files()


if __name__ == '__main__':
    args = parse_args()
    main(args)
