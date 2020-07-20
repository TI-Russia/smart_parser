from declarations.input_json import TSourceDocument, TDeclaratorReference, TDlrobotHumanFile, TWebReference, TIntersectionStatus

import shutil
import os
import argparse
import hashlib
import json
import logging
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-folder", dest='dlrobot_folder', required=True)
    parser.add_argument("--human-json", dest='human_json', default="human_files.json")
    parser.add_argument("--old-dlrobot-human-json", dest='old_dlrobot_human_json', required=False)
    parser.add_argument("--use-v", dest='old_dlrobot_human_json', required=False)
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")
    parser.add_argument("--overwrite-existing", dest='skip_existing', action="store_false", default=True)
    parser.add_argument("--copy-to-one-folder-json", dest='copy_to_one_folder_json', required=True)
    parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)
    parser.add_argument("--rebuild-office-to-domain", dest='rebuild_office_to_domain', action="store_true", default=False)

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
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    return logger


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


class TJoiner:
    human_file_name_prefix = "h"
    old_file_name_prefix = "o"

    def __init__(self, args, logger):
        self.args = args
        self.logger = logger

        self.logger.info("load {}".format(args.human_json))
        self.dlrobot_human = TDlrobotHumanFile (args.human_json)
        self.saved_declarator_folder = self.dlrobot_human.document_folder
        self.dlrobot_human.document_folder = args.dlrobot_folder

        with open(args.copy_to_one_folder_json, "r", encoding="utf") as inp:
            self.file_to_urls = json.load(inp)

    def add_dlrobot_files(self, domain):
        self.logger.debug("process {}".format(domain))
        domain_folder = os.path.join(self.args.dlrobot_folder, domain)
        if not os.path.isdir(domain_folder):
            return
        new_files_found_by_dlrobot = 0
        files_count = 0
        files_to_urls = self.file_to_urls.get(domain)
        for base_file_name in os.listdir(domain_folder):
            file_path = os.path.join(domain_folder, base_file_name)
            if file_path.endswith(".json") or file_path.endswith(".txt"):
                continue
            # we can call join_human_and_dlrobot many times
            if base_file_name.startswith(TJoiner.human_file_name_prefix) or base_file_name.startswith(TJoiner.old_file_name_prefix):
                continue
            files_count += 1

            web_ref = TWebReference()
            web_ref.url = files_to_urls[os.path.basename(file_path)]
            web_ref.crawl_epoch = args.crawl_epoch

            sha256 = build_sha256(file_path)
            src_doc = self.dlrobot_human.document_collection.get(sha256)
            relative_path = os.path.join(domain, os.path.basename(file_path))
            if src_doc is not None:
                self.logger.error("a file copy found: {}/{}".format(domain_folder, base_file_name))
                src_doc.intersection_status = TIntersectionStatus.both_found
                src_doc.document_path = relative_path
                src_doc.add_web_reference(web_ref)
            else:
                src_doc = TSourceDocument()
                src_doc.document_path = os.path.basename(file_path)
                src_doc.intersection_status = TIntersectionStatus.only_dlrobot
                src_doc.document_path = relative_path
                src_doc.add_web_reference(web_ref)
                self.dlrobot_human.document_collection[sha256] = src_doc
                new_files_found_by_dlrobot += 1

        self.logger.debug("files: {},  new_files_found_by_dlrobot: {}".format(files_count, new_files_found_by_dlrobot))

    def copy_human_file(self, src_doc: TSourceDocument):
        ref = src_doc.decl_references[0]
        web_site = ref.web_domain
        if web_site == "" or web_site is None:
            web_site = "unknown_domain"
        infile = os.path.join(self.saved_declarator_folder, src_doc.document_path)
        src_doc.document_path = os.path.join(web_site, TJoiner.human_file_name_prefix + os.path.basename(infile))
        outfile = self.dlrobot_human.get_document_path(src_doc)
        output_folder = os.path.dirname(outfile)
        if not os.path.exists(output_folder):
            self.logger.debug("create folder for domain {}".format(output_folder))
            os.mkdir(output_folder)
        if args.skip_existing and os.path.exists(outfile):
            self.logger.debug("skip copy {}, it exists".format(outfile))
        else:
            self.logger.debug("copy {} to {}".format(infile, outfile))
            if not os.path.exists(infile):
                self.logger.error("Error! Cannot copy {}, the file does not exists".format(infile))
                return
            else:
                shutil.copyfile(infile, outfile)

    def copy_old_dlrobot_files(self, json_file_name):
        self.logger.info( "read {}".format(json_file_name) )
        old_json = TDlrobotHumanFile (json_file_name)

        self.logger.info("copy old files ...")
        for sha256, src_doc  in old_json.document_collection.items():
            if sha256  not in self.dlrobot_human.document_collection:
                infile = old_json.get_document_path(src_doc, absolute=True)
                if not os.path.exists(infile):
                    self.logger.error("old file {} does not exist".format(infile))
                else:
                    folder = os.path.dirname(src_doc.document_path)
                    if not os.path.exists(folder):
                        self.logger.debug("create folder for domain {}".format(folder))
                        os.mkdir(folder)
                    output_basename = os.path.basename(src_doc.document_path)
                    if not output_basename.startswith(TJoiner.old_file_name_prefix):
                        output_basename = TJoiner.old_file_name_prefix + output_basename
                    src_doc.document_path = os.path.join(folder, output_basename)
                    self.dlrobot_human.document_collection[sha256] = src_doc
                    outfile = self.dlrobot_human.get_document_path(src_doc)
                    self.logger.debug("copy {} to {}".format(infile, outfile))
                    shutil.copyfile(infile, outfile)

    def join(self):
        self.logger.info("register dlrobot files ...")
        for domain in os.listdir(self.args.dlrobot_folder):
            if domain != "unknown_domain":
                self.add_dlrobot_files(domain)

        self.logger.info("copy human files ...")
        for src_doc in self.dlrobot_human.document_collection.values():
            if src_doc.intersection_status == TSourceDocument.only_human:
                self.copy_human_file(src_doc)

        if args.old_dlrobot_human_json is not None:
            self.copy_old_dlrobot_files(args.old_dlrobot_human_json)

    def calc_office_id(self):
        web_site_to_office = dict()
        self.logger.info("web_site_to_office")
        for src_doc in self.dlrobot_human.document_collection.values():
            for r in src_doc.decl_references:
                if r.web_domain not in web_site_to_office:
                    web_site_to_office[r.web_domain] = defaultdict(int)
                    web_site_to_office[r.web_domain][r.office_id] += 1

        web_domain_to_office = dict()
        for web_site, offices in web_site_to_office.items():
            office_id = max(offices.keys(), key=lambda x: offices[x])
            web_domain_to_office[web_site] = office_id

        print(web_domain_to_office)
        self.logger.info("update calculated_office_id...")

        for src_doc in self.dlrobot_human.document_collection.values():
            office_id = None
            for r in src_doc.decl_references:
                office_id = r.office_id
                break
            if office_id is None:
                web_domain = os.path.dirname(src_doc.document_path)
                office_id = web_domain_to_office.get(web_domain)
            if office_id is not None:
                self.logger.debug("set file {} calculated_office_id={}".format(src_doc.document_path, office_id))
                src_doc.calculated_office_id = office_id


def main(args):
    logger = setup_logging("join_human_and_dlrobot.log")
    joiner = TJoiner(args, logger)
    if not args.rebuild_office_to_domain:
        joiner.join()
    joiner.calc_office_id()

    for src_doc in joiner.dlrobot_human.document_collection.values():
        assert os.path.exists(joiner.dlrobot_human.get_document_path(src_doc, absolute=True))
        if src_doc.calculated_office_id is None:
            logger.error("file {} has no office".format(src_doc.document_path))

    joiner.dlrobot_human.write(args.output_json)

if __name__ == '__main__':
    args = parse_args()
    main(args)
