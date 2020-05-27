import shutil
import os
import argparse
import hashlib
import json
from disclosures.declarations.dlrobot_human_common import dhjs
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-folder", dest='dlrobot_folder', default='dlrobot-folder')
    parser.add_argument("--human-json", dest='human_json', default="human_files.json")
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")
    parser.add_argument("--skip-existing", dest='skip_existing', action="store_true", default=False)
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


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


class TJoiner:
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
        for f in os.listdir(domain_folder):
            file_path = os.path.join(domain_folder, f)
            if file_path.endswith(".json") or file_path.endswith(".txt"):
                continue
            files_count += 1
            sha256 = build_sha256(file_path)
            if sha256 in self.human_json:
                domain_info[sha256] = self.human_json[sha256]
                domain_info[sha256][dhjs.intersection_status] = dhjs.both_found
                self.found_by_dlrobot.add(sha256)
            else:
                domain_info[sha256] = {
                    dhjs.intersection_status: dhjs.only_dlrobot
                }
                new_files_found_by_dlrobot += 1
            domain_info[sha256][dhjs.dlrobot_path] = f
        self.dlrobot_human_json[domain] = domain_info
        self.logger.debug("files: {},  new_files_found_by_dlrobot: {}".format(files_count, new_files_found_by_dlrobot))

    def copy_human_file(self, sha256, file_info):
        domain = file_info[dhjs.web_domain]
        if domain == "":
            domain = "unknown_domain"
        folder = os.path.join(args.dlrobot_folder, domain)
        if not os.path.exists(folder):
            self.logger.debug("create folder for domain {}".format(folder))
            os.mkdir(folder)
        infile = file_info[dhjs.filepath]
        outfile = os.path.join(folder, "h" + os.path.basename(infile))
        if args.skip_existing and os.path.exists(outfile):
            self.logger.debug("skip copy {}, it exists".format(outfile))
        else:
            self.logger.debug("copy {} to {}".format(infile, outfile))
            if not os.path.exists(infile):
                self.logger.error("Error! Cannot copy {}".format(infile))
            else:
                shutil.copyfile(infile, outfile)
            file_info[dhjs.dlrobot_path] = os.path.basename(outfile)
            file_info[dhjs.intersection_status] = dhjs.only_human
        self.dlrobot_human_json.get(domain, dict())[sha256] = file_info

    def join(self):
        for domain in os.listdir(self.args.dlrobot_folder):
            try:
                self.process_domain(domain)
            except Exception as exp:
                self.logger.error("Error on {}: {}, keep going".format(domain, exp))

        for sha256, file_info in self.human_json.items():
            try:
                if sha256 not in self.found_by_dlrobot:
                    self.copy_human_file(sha256, file_info)
            except Exception as exp:
                self.logger.error("Error on {} : {}, keep going".format(sha256, exp))

        self.logger.info("write {}".format(self.args.output_json))


def main(args):
    logger = setup_logging("join_human_and_dlrobot.log")
    joiner = TJoiner(args, logger)
    joiner.join()
    with open(args.output_json, "w") as out:
        json.dump(joiner.dlrobot_human_json, out, indent=4)


if __name__ == '__main__':
    args = parse_args()
    main(args)