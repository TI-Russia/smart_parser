from declarations.input_json import TSourceDocument, TDlrobotHumanFile, TWebReference, TIntersectionStatus
import shutil
import os
import re
import argparse
import hashlib
import logging
from collections import defaultdict
from robots.common.robot_project import TRobotProject


def parse_args():
    parser = argparse.ArgumentParser()
    #input args
    parser.add_argument("--max-ctime", dest='max_ctime', required=True, type=int, help="max ctime of an input folder")
    parser.add_argument("--input-dlrobot-folder", dest='input_dlrobot_folder', required=True)
    parser.add_argument("--human-json", dest='human_json', required=True)
    parser.add_argument("--old-dlrobot-human-json", dest='old_dlrobot_human_json', required=False)


    #output args
    parser.add_argument("--output-domains-folder", dest='output_domains_folder', required=True)
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")

    #options
    parser.add_argument("--only-rebuild-office-to-domain", dest='only_rebuild_office_to_domain', action="store_true", default=False)

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
        if os.path.exists(args.output_domains_folder):
            self.logger.debug("rmdir {}".format(args.output_domains_folder))
            shutil.rmtree(args.output_domains_folder)
        self.output_dlrobot_human = TDlrobotHumanFile(args.output_json, read_db=False, document_folder=args.output_domains_folder)
        self.skipped_files_count = 0
        self.web_domain_file_count = defaultdict(int)

    def create_folder_if_absent(self, folder):
        if not os.path.exists(folder):
            self.logger.debug("create folder {}".format(folder))
            os.mkdir(folder)

    def copy_dlrobot_file(self, web_domain, input_file_path, intersection_status, web_ref=None, decl_ref=None):
        sha256 = build_sha256(input_file_path)
        src_doc = self.output_dlrobot_human.document_collection.get(sha256)
        new_file = src_doc is None
        if new_file:
            src_doc = TSourceDocument()
        else:
            self.logger.debug("a file copy found: {}".format(input_file_path))

        src_doc.update_intersection_status(intersection_status)
        src_doc.add_web_reference(web_ref)
        src_doc.add_decl_reference(decl_ref)

        if new_file:
            self.web_domain_file_count[web_domain] += 1
            _, extension = os.path.splitext(input_file_path)
            src_doc.document_path = os.path.join(web_domain, str(self.web_domain_file_count[web_domain]) + extension)
            src_doc.add_web_reference(web_ref)
            if not os.path.exists(input_file_path):
                self.logger.error("source file {} does not exist, cannot copy it".format(input_file_path))
                return new_file
            else:
                self.output_dlrobot_human.document_collection[sha256] = src_doc
                absolute_output_path = self.output_dlrobot_human.get_document_path(src_doc, absolute=True)
                self.create_folder_if_absent(os.path.dirname(absolute_output_path))
                self.logger.debug("copy {} to {}".format(input_file_path, absolute_output_path))
                shutil.copyfile(input_file_path, absolute_output_path)

        assert os.path.exists(self.output_dlrobot_human.get_document_path(src_doc, absolute=True))

        return new_file

    def copy_files_of_one_web_site(self, crawl_result_folder, web_site, file_urls):
        input_folder = os.path.join(crawl_result_folder, web_site)

        with os.scandir(input_folder) as it:
            for entry in it:
                if entry.is_file():
                    base_file_name = entry.name
                    # ignore trash files
                    if base_file_name.endswith(".json") or base_file_name.endswith(".txt") \
                            or base_file_name.startswith("tmp"):
                        continue
                    reference_url = file_urls.get(base_file_name)
                    if reference_url is None:
                        self.logger.error(
                            "file {} in {} cannot be found in the dlrobot project. skip it".format(base_file_name,
                                                                                                   web_site))
                        self.skipped_files_count += 1
                        continue
                    input_file_path = os.path.join(input_folder, base_file_name)
                    web_ref = TWebReference(url=reference_url, crawl_epoch=self.args.max_ctime)
                    self.copy_dlrobot_file(web_site, input_file_path, TIntersectionStatus.only_dlrobot, web_ref)

    def read_file_urls_from_dlrobot_project(self, robot_project_path):
        file_info = {}
        try:
            with TRobotProject(self.logger, robot_project_path, [], None, enable_selenium=False, enable_search_engine=False) as project:
                project.read_project(fetch_morda_url=False, check_step_names=False)
                office_info = project.offices[0]
                for export_record in office_info.export_env.exported_files:
                    url = export_record.url
                    export_path = os.path.basename(export_record.export_path)
                    file_info[export_path] = url
                return file_info
        except Exception as exp:
            self.logger.debug("Fail on {}, exception={}".format(robot_project_path, exp))

    def copy_files_of_one_project(self, entry: os.DirEntry):
        dlrobot_project = entry.name
        self.logger.debug("process {}".format(dlrobot_project))
        project_folder = os.path.join(self.args.input_dlrobot_folder, dlrobot_project)
        dlrobot_project_without_timestamp = re.sub('\.[0-9]+$', '', dlrobot_project)
        robot_project = os.path.join(project_folder, dlrobot_project_without_timestamp + ".txt")
        if not os.path.exists(robot_project):
            self.logger.error("no dlrobot project file found".format(project_folder))
            return
        file_info = self.read_file_urls_from_dlrobot_project(robot_project)
        if file_info is None:
            self.logger.error("cannot get reference urls from {}".format(robot_project))
            return
        crawl_result_folder = os.path.join(project_folder, "result")
        if not os.path.exists(crawl_result_folder):
            self.logger.debug("no crawl result folder found in {}, skip it".format(project_folder))
            return
        with os.scandir(crawl_result_folder) as it:
            for entry in it:
                if entry.is_dir():
                    self.copy_files_of_one_web_site(crawl_result_folder, entry.name, file_info)

    def copy_new_dlrobot_files(self):
        self.logger.info("copy dlrobot files from {} ...".format(self.args.input_dlrobot_folder))
        with os.scandir(self.args.input_dlrobot_folder) as it:
            for entry in it:
                if entry.is_dir() and entry.stat().st_ctime < self.args.max_ctime:
                    self.copy_files_of_one_project(entry)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))
        if self.skipped_files_count > 0:
            self.logger.info("orphan files: {} (files are present in result folder, but are not in the projects".format(self.skipped_files_count))

    def copy_old_dlrobot_files(self):
        self.logger.info("read {}".format(args.old_dlrobot_human_json))
        old_json = TDlrobotHumanFile(args.old_dlrobot_human_json)

        self.logger.info("copy old files ...")
        for sha256, src_doc in old_json.document_collection.items():
            if sha256 in self.output_dlrobot_human.document_collection:
                continue
            if src_doc.intersection_status == TSourceDocument.only_human:
                continue
            input_file_path = old_json.get_document_path(src_doc, absolute=True)
            web_domain = os.path.dirname(src_doc.document_path)
            assert (web_domain.find('/') == -1)
            self.copy_dlrobot_file(web_domain, input_file_path, src_doc.intersection_status,
                                   src_doc.web_references[0])
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def copy_human_files(self):
        self.logger.info("read {}".format(self.args.human_json))
        human_files = TDlrobotHumanFile(self.args.human_json)
        self.logger.info("copy human files ...")
        for src_doc in human_files.document_collection.values():
            decl_ref = src_doc.decl_references[0]
            web_site = decl_ref.web_domain
            if web_site == "" or web_site is None:
                web_site = "unknown_domain"
            input_file_path = human_files.get_document_path(src_doc, absolute=True)
            self.copy_dlrobot_file(web_site, input_file_path, TIntersectionStatus.only_human, None, decl_ref)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def copy_old_human_files_that_were_deleted_in_declarator(self):
        self.logger.info("read {}".format(args.old_dlrobot_human_json))
        old_json = TDlrobotHumanFile(args.old_dlrobot_human_json)

        self.logger.info("copy_old_human_files_that_were_deleted_in_declarator ...")
        for sha256, src_doc in old_json.document_collection.items():
            if sha256 in self.output_dlrobot_human.document_collection:
                continue
            if src_doc.intersection_status != TSourceDocument.only_human:
                continue
            input_file_path = old_json.get_document_path(src_doc, absolute=True)
            web_domain = os.path.dirname(src_doc.document_path)
            assert (web_domain.find('/') == -1)
            if len(src_doc.decl_references) == 0:
                self.logger.error("file {}  has  not reference to declarator".format(input_file_path))
                continue
            decl_ref = src_doc.decl_references[0]
            decl_ref.deleted_in_declarator_db = True
            self.copy_dlrobot_file(web_domain, input_file_path, TIntersectionStatus.only_human,
                                   None, decl_ref)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def calc_office_id(self):
        web_site_to_office = dict()
        self.logger.info("web_site_to_office")
        for src_doc in self.output_dlrobot_human.document_collection.values():
            for r in src_doc.decl_references:
                if r.web_domain not in web_site_to_office:
                    web_site_to_office[r.web_domain] = defaultdict(int)
                    web_site_to_office[r.web_domain][r.office_id] += 1

        web_domain_to_office = dict()
        for web_site, offices in web_site_to_office.items():
            office_id = max(offices.keys(), key=lambda x: offices[x])
            web_domain_to_office[web_site] = office_id

        self.logger.info("update calculated_office_id...")

        for src_doc in self.output_dlrobot_human.document_collection.values():
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
    if not args.only_rebuild_office_to_domain:
        joiner.copy_new_dlrobot_files()
        joiner.copy_old_dlrobot_files()
        joiner.copy_human_files()
        joiner.copy_old_human_files_that_were_deleted_in_declarator()
        joiner.output_dlrobot_human.write()

    joiner.calc_office_id()

    for src_doc in joiner.output_dlrobot_human.document_collection.values():
        if src_doc.calculated_office_id is None:
            logger.error("file {} has no office".format(src_doc.document_path))

    joiner.output_dlrobot_human.write()


if __name__ == '__main__':
    args = parse_args()
    main(args)
