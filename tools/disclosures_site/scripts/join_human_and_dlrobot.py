from declarations.input_json import TSourceDocument, TDlrobotHumanFile, TWebReference
from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.robot_project import TRobotProject
from common.logging_wrapper import setup_logging
from common.export_files import TExportFile

import os
import sys
import re
import argparse


class TJoiner:

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        # input args
        parser.add_argument("--max-ctime", dest='max_ctime', required=True, type=int,
                            help="max ctime of an input folder")
        parser.add_argument("--input-dlrobot-folder", dest='input_dlrobot_folder', required=True)
        parser.add_argument("--human-json", dest='human_json', required=True)
        parser.add_argument("--old-dlrobot-human-json", dest='old_dlrobot_human_json', required=False)

        # output args
        parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")

        # options
        parser.add_argument("--only-rebuild-office-to-domain", dest='only_rebuild_office_to_domain',
                            action="store_true", default=False)

        return parser.parse_args(arg_list)

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="join_human_and_dlrobot.log", append_mode=True)
        self.output_dlrobot_human = TDlrobotHumanFile(args.output_json, read_db=False)
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.web_sites.load_from_disk()
        self.old_files_with_office_count = 0

    def add_dlrobot_file(self, sha256, file_extension, web_refs=[], decl_refs=[], declaration_year=None):
        src_doc = self.output_dlrobot_human.document_collection.get(sha256)
        if src_doc is None:
            src_doc = TSourceDocument()
            src_doc.file_extension = file_extension
            self.output_dlrobot_human.document_collection[sha256] = src_doc
        for web_ref in web_refs:
            src_doc.add_web_reference(web_ref)
        for decl_ref in decl_refs:
            src_doc.add_decl_reference(decl_ref)

    def read_export_file_from_dlrobot_project(self, robot_project_path):
        file_info = {}
        try:
            with TRobotProject(self.logger, robot_project_path, [], None, enable_selenium=False, enable_search_engine=False) as project:
                project.read_project(check_step_names=False)
                office_info = project.web_site_snapshots[0]
                for export_record in office_info.export_env.exported_files:
                    file_info[export_record.sha256] = export_record
                return file_info
        except Exception as exp:
            self.logger.debug("Fail on {}, exception={}".format(robot_project_path, exp))

    def add_files_of_one_project(self, dlrobot_project):
        self.logger.debug("process {}".format(dlrobot_project))
        project_folder = os.path.join(self.args.input_dlrobot_folder, dlrobot_project)
        dlrobot_project_without_timestamp = re.sub('\.[0-9]+$', '', dlrobot_project)
        robot_project = os.path.join(project_folder, dlrobot_project_without_timestamp + ".txt")
        if not os.path.exists(robot_project):
            self.logger.error("no dlrobot project file found".format(project_folder))
            return
        exported_files = self.read_export_file_from_dlrobot_project(robot_project)
        if exported_files is None:
            self.logger.error("cannot get exported files from {}".format(robot_project))
            return
        file_info: TExportFile
        for sha256, file_info in exported_files.items():
            web_domain = dlrobot_project_without_timestamp
            web_ref = TWebReference(
                url=file_info.url,
                crawl_epoch=self.args.max_ctime,
                web_domain=web_domain,
                declaration_year=file_info.declaration_year
            )
            self.add_dlrobot_file(sha256, file_info.file_extension, [web_ref])

    def add_new_dlrobot_files(self):
        self.logger.info("copy dlrobot files from {} ...".format(self.args.input_dlrobot_folder))
        with os.scandir(self.args.input_dlrobot_folder) as it:
            for entry in it:
                if entry.is_dir() and entry.stat().st_ctime < self.args.max_ctime:
                    self.add_files_of_one_project(entry.name)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def add_old_dlrobot_files(self):
        self.logger.info("read {}".format(self.args.old_dlrobot_human_json))
        old_json = TDlrobotHumanFile(self.args.old_dlrobot_human_json)
        self.logger.info("copy old files ...")
        self.old_files_with_office_count = 0
        for sha256, src_doc in old_json.document_collection.items():
            if src_doc.calculated_office_id is not None:
                self.old_files_with_office_count += 1
            self.add_dlrobot_file(sha256, src_doc.file_extension,
                                  web_refs=src_doc.web_references, decl_refs=src_doc.decl_references)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def add_human_files(self):
        self.logger.info("read {}".format(self.args.human_json))
        human_files = TDlrobotHumanFile(self.args.human_json)
        self.logger.info("add human files ...")
        for sha256, src_doc in human_files.document_collection.items():
            self.add_dlrobot_file(sha256, src_doc.file_extension, decl_refs=src_doc.decl_references)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def calc_office_id(self):
        for sha256, src_doc in self.output_dlrobot_human.document_collection.items():
            office_id = None
            for r in src_doc.decl_references:
                office_id = r.office_id
                break

            if office_id is None:
                for web_ref in src_doc.web_references:
                    web_site = self.web_sites.get_web_site(web_ref.web_domain)
                    if web_site is not None:
                        office_id = web_site.calculated_office_id
                        break

            if office_id is not None:
                self.logger.debug("set file {} calculated_office_id={}".format(sha256, office_id))
                src_doc.calculated_office_id = office_id

    def main(self):
        if not self.args.only_rebuild_office_to_domain:
            self.add_new_dlrobot_files()
            if self.args.old_dlrobot_human_json is not None:
                self.add_old_dlrobot_files()
            self.add_human_files()
            self.output_dlrobot_human.write()

        self.calc_office_id()

        files_count_with_office_id = 0

        for sha256, src_doc in self.output_dlrobot_human.document_collection.items():
            if src_doc.calculated_office_id is None:
                self.logger.error("website: {}, file {} has no office".format(src_doc.get_web_site(), sha256))
            else:
                files_count_with_office_id += 1
        self.logger.info("all files count = {}, files_count_with_office_id = {}".format(
                len(self.output_dlrobot_human.document_collection), files_count_with_office_id))

        self.output_dlrobot_human.write()

        if self.old_files_with_office_count > files_count_with_office_id:
            error = "old db has more files than the new one, stop processing (self.old_files_with_office_count > files_count_with_office_id)"
            self.logger.error(error)
            raise Exception(error)


if __name__ == '__main__':
    TJoiner(TJoiner.parse_args(sys.argv[1:])).main()

