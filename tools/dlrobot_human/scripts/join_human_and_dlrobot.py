from dlrobot_human.dlrobot_human_dbm import TDlrobotHumanFileDBM
from dlrobot_human.input_document import TWebReference, TSourceDocument
from dlrobot.common.robot_project import TRobotProject
from dlrobot.common.robot_config import TRobotConfig
from dlrobot.common.robot_web_site import TWebSiteCrawlSnapshot
from common.logging_wrapper import setup_logging
from common.export_files import TExportFile
from office_db.web_site_list import TDeclarationWebSiteList

import os
import sys
import re
import argparse


class TJoiner:

    @staticmethod
    def parse_args(arg_list):
        default_ml_model_path = os.path.join(os.path.dirname(__file__), "../predict_office/model")
        parser = argparse.ArgumentParser()
        # input args
        parser.add_argument("--max-ctime", dest='max_ctime', required=True, type=int,
                            help="max ctime of an input folder")
        parser.add_argument("--input-dlrobot-folder", dest='input_dlrobot_folder', required=True)
        parser.add_argument("--human-json", dest='human_json', required=True)
        parser.add_argument("--old-dlrobot-human-json", dest='old_dlrobot_human_json', required=False)
        parser.add_argument("--office-model-path", dest='office_model_path', required=False,
                            default=default_ml_model_path)

        # output args
        parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")

        return parser.parse_args(arg_list)

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="join_human_and_dlrobot.log", append_mode=True)
        self.output_dlrobot_human = TDlrobotHumanFileDBM(args.output_json)
        self.output_dlrobot_human.create_db()
        self.old_files_with_office_count = 0
        self.web_sites_db = TDeclarationWebSiteList(self.logger)
        self.offices = self.web_sites_db.offices
        self.dlrobot_config = TRobotConfig.read_by_config_type("prod")

    def add_dlrobot_file(self, sha256, file_extension, web_refs=[], decl_refs=[]):
        src_doc = self.output_dlrobot_human.get_document_maybe(sha256)
        if src_doc is None:
            src_doc = TSourceDocument(file_extension)
            self.output_dlrobot_human.update_source_document(sha256, src_doc)
        for web_ref in web_refs:
            src_doc.add_web_reference(web_ref)
        for decl_ref in decl_refs:
            src_doc.add_decl_reference(decl_ref)
        self.output_dlrobot_human.update_source_document(sha256, src_doc)

    def add_files_of_one_project(self, dlrobot_project):
        self.logger.debug("process {}".format(dlrobot_project))
        project_folder = os.path.join(self.args.input_dlrobot_folder, dlrobot_project)
        dlrobot_project_without_timestamp = re.sub('\.[0-9]+$', '', dlrobot_project)
        project_path = os.path.join(project_folder, dlrobot_project_without_timestamp + ".txt")
        if not os.path.exists(project_path):
            self.logger.error("no dlrobot project file found".format(project_folder))
            return
        try:
            project = TRobotProject(self.logger, project_path, config=self.dlrobot_config, web_sites_db=self.web_sites_db)
            project.read_project(check_step_names=False)
            office_info: TWebSiteCrawlSnapshot
            office_info = project.web_site_snapshots[0]
            site_url = office_info.get_site_url()
            exported_files = dict()
            for export_record in office_info.export_env.exported_files:
                exported_files[export_record.sha256] = export_record
        except Exception as exp:
            self.logger.error("cannot read project {}, exp={}".format(project_path, exp))
            return

        file_info: TExportFile
        for sha256, file_info in exported_files.items():
            web_ref = TWebReference(
                url=file_info.url,
                crawl_epoch=self.args.max_ctime,
                site_url=site_url,
                declaration_year=file_info.declaration_year
            )
            self.add_dlrobot_file(sha256, file_info.file_extension, [web_ref])

    def add_new_dlrobot_files(self):
        self.logger.info("copy dlrobot files from {} ...".format(self.args.input_dlrobot_folder))
        with os.scandir(self.args.input_dlrobot_folder) as it:
            for entry in it:
                if entry.is_dir():
                    if entry.stat().st_ctime < self.args.max_ctime:
                        self.add_files_of_one_project(entry.name)
                    else:
                        self.logger.debug("skip too young folder {}".format(entry.name))

        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def add_old_dlrobot_files(self):
        self.logger.info("read {}".format(self.args.old_dlrobot_human_json))
        old_json = TDlrobotHumanFileDBM(self.args.old_dlrobot_human_json)
        old_json.open_db_read_only()
        self.logger.info("copy old files ...")
        self.old_files_with_office_count = 0
        for sha256, src_doc in old_json.get_all_documents():
            if src_doc.calculated_office_id is not None:
                self.old_files_with_office_count += 1
            self.add_dlrobot_file(sha256, src_doc.file_extension,
                                  web_refs=src_doc.web_references, decl_refs=src_doc.decl_references)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def is_new_fns_document_from_declarator(self, src_doc: TSourceDocument):
        for ref in src_doc.decl_references:
            if 9542 <= ref.office_id <= 10611:
                # this document is already imported from fns but with a different sha256
                return True
        return False

    def check_declaration_office(self, sha256, src_doc: TSourceDocument):
        for ref in src_doc.decl_references:
            if ref.office_id is not None and ref.office_id not in self.offices.offices:
                raise Exception("document sha256={} office {} is not registered in disclosures".format(sha256, ref.office_id))

    def add_human_files(self):
        self.logger.info("read {}".format(self.args.human_json))
        human_files = TDlrobotHumanFileDBM(self.args.human_json)
        human_files.open_db_read_only()
        self.logger.info("add human files ...")
        for sha256, src_doc in human_files.get_all_documents():
            if not self.is_new_fns_document_from_declarator(src_doc):
                self.check_declaration_office(sha256, src_doc)
                self.add_dlrobot_file(sha256, src_doc.file_extension, decl_refs=src_doc.decl_references)
        self.logger.info("Database Document Count: {}".format(self.output_dlrobot_human.get_documents_count()))

    def main(self):
        self.add_new_dlrobot_files()
        if self.args.old_dlrobot_human_json is not None:
            self.add_old_dlrobot_files()
        self.add_human_files()
        self.output_dlrobot_human.close_db()


if __name__ == '__main__':
    TJoiner(TJoiner.parse_args(sys.argv[1:])).main()

