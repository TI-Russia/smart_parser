import shutil
import os
import argparse
import hashlib
import json
from disclosures.declarations.dlrobot_human_common import dhjs
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-folder", dest='dlrobot_folder', required=True)
    parser.add_argument("--human-json", dest='human_json', default="human_files.json")
    parser.add_argument("--old-dlrobot-human-json", dest='old_dlrobot_human_json', required=False)
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
            self.logger.debug("copy {} to {}".format(infile, outfile))
            if not os.path.exists(infile):
                self.logger.error("Error! Cannot copy {}".format(infile))
            else:
                shutil.copyfile(infile, outfile)
            file_info[dhjs.dlrobot_path] = os.path.basename(outfile)
            file_info[dhjs.intersection_status] = dhjs.only_human
        if web_site not in self.dlrobot_human_json:
            self.dlrobot_human_json[web_site] = dict()
        self.dlrobot_human_json.get(web_site][sha256] = file_info

    def copy_old_dlrobot_file(self, web_site, sha256, infile):
        folder = os.path.join(args.dlrobot_folder, web_site)
        if not os.path.exists(folder):
            self.logger.debug("create folder for domain {}".format(folder))
            os.mkdir(folder)
        outfile = os.path.join(folder, "o" + os.path.basename(infile))
        self.logger.debug("copy {} to {}".format(infile, outfile))
        shutil.copyfile(infile, outfile)
        file_info = {
            dhjs.dlrobot_path: os.path.basename(outfile),
            dhjs.intersection_status: dhjs.only_dlrobot,
            dhjs.dlrobot_copied_from_the_past: True
        }
        self.dlrobot_human_json.get[web_site][sha256] = file_info

    def get_old_dlrobot_files(self, json_file_name):
        with open(json_file_name), "r") as inp:
            old_json = json.load(inp)
        if dhjs.dlrobot_path in old_json:
            web_domains = old_json[dhjs.file_collection]
            dlrobot_path = old_json[dhjs.dlrobot_path]
        else:
            web_domains = old_json
            dlrobot_path = os.path.dirname(json_file_name)
        for web_domain, files in web_domains.items():
            for sha256, file_info in files.items():
                path = file_info.get(dhjs.dlrobot_path, file_info.get("dlrobot_path"))
                assert is not None
                path = os.path.join(dlrobot_path, path)
                if os.path.exists(path)
                    self.logger.error("old file {} does not exist".format(path))
                else
                    yield  web_domain, sha256, path

    def join(self):
        for domain in os.listdir(self.args.dlrobot_folder):
            try:
                self.process_domain(domain)
            except Exception as exp:
                self.logger.error("Error on {}: {}, keep going".format(domain, exp))

        for sha256, file_info in self.human_json[dhjs.file_collection].items():
            try:
                if sha256 not in self.found_by_dlrobot:
                    self.copy_human_file(sha256, file_info)
            except Exception as exp:
                self.logger.error("Error on file {}, exception={}, keep going".format(sha256, exp))

        if args.old_dlrobot_human_json is not None:
            for web_site, sha256, filename in self.get_old_dlrobot_files(args.old_dlrobot_human_json):
                if web_site not in self.dlrobot_human_json:
                    self.dlrobot_human_json[web_site] = dict()
                if sha256 not in self.dlrobot_human_json[web_site]:
                    self.copy_old_file(web_site, sha256, filename)


def main(args):
    logger = setup_logging("join_human_and_dlrobot.log")
    joiner = TJoiner(args, logger)
    joiner.join()
    with open(args.output_json, "w") as out:
        output_json  = {
            dhjs.declarator_folder: joiner.human_json[dhjs.declarator_folder],
            dhjs.dlrobot_folder: args.dlrobot_folder,
            dhjs.file_collection: joiner.dlrobot_human_json
        }
        json.dump(output_json, out,  indent=4)


if __name__ == '__main__':
    args = parse_args()
    main(args)
