from declarations.input_json import TSourceDocument, TDlrobotHumanFile, TWebReference
from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.robot_project import TRobotProject
from web_site_db.robot_web_site import TWebSiteCrawlSnapshot
from common.logging_wrapper import setup_logging
from common.export_files import TExportFile
from predict_office.prediction_case import  TPredictionCase
from predict_office.tensor_flow_office import TTensorFlowOfficeModel
from common.urllib_parse_pro import urlsplit_pro
from smart_parser_http.smart_parser_client import TSmartParserCacheClient

from collections import defaultdict
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
        parser.add_argument("--office-model-path", dest='office_model_path', required=False)


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
        bigrams_path = os.path.join(args.office_model_path, "office_ngrams.txt")
        ml_model_path = os.path.join(args.office_model_path, "model")
        self.office_ml_model = TTensorFlowOfficeModel(self.logger, bigrams_path, ml_model_path)
        sp_args = TSmartParserCacheClient.parse_args([])
        self.smart_parser_server_client = TSmartParserCacheClient(sp_args, self.logger)

    def add_dlrobot_file(self, sha256, file_extension, web_refs=[], decl_refs=[]):
        src_doc = self.output_dlrobot_human.document_collection.get(sha256)
        if src_doc is None:
            src_doc = TSourceDocument()
            src_doc.file_extension = file_extension
            self.output_dlrobot_human.document_collection[sha256] = src_doc
        for web_ref in web_refs:
            src_doc.add_web_reference(web_ref)
        for decl_ref in decl_refs:
            src_doc.add_decl_reference(decl_ref)

    def add_files_of_one_project(self, dlrobot_project):
        self.logger.debug("process {}".format(dlrobot_project))
        project_folder = os.path.join(self.args.input_dlrobot_folder, dlrobot_project)
        dlrobot_project_without_timestamp = re.sub('\.[0-9]+$', '', dlrobot_project)
        project_path = os.path.join(project_folder, dlrobot_project_without_timestamp + ".txt")
        if not os.path.exists(project_path):
            self.logger.error("no dlrobot project file found".format(project_folder))
            return
        try:
            project = TRobotProject(self.logger, project_path, [], None)
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

    def predict_office_deterministic_web_domain(self, src_doc: TSourceDocument):
        web_ref: TWebReference
        for web_ref in src_doc.web_references:
            web_domain = urlsplit_pro(web_ref._site_url).hostname
            det_office_id = self.office_ml_model.get_office_id_by_deterministic_web_domain(web_domain)
            if det_office_id is not None:
                src_doc.calculated_office_id = det_office_id
                self.logger.debug("set file {} office_id={} (deterministic web domain \"{}\")".format(sha256,
                                                                                                      det_office_id,
                                                                                                      web_domain))
                return True
        return False

    def calc_office_id(self):
        predict_cases = list()
        src_doc: TSourceDocument
        for sha256, src_doc in self.output_dlrobot_human.document_collection.items():
            if len(src_doc.decl_references) > 0:
                src_doc.calculated_office_id = src_doc.decl_references[0].office_id
                self.logger.debug("set file {} office_id={} (from declarator)".format(sha256,
                                                                                      src_doc.calculated_office_id))
            elif self.predict_office_deterministic_web_domain(src_doc):
                pass
            else:
                web_ref: TWebReference
                for web_ref in src_doc.web_references:
                    web_domain = urlsplit_pro(web_ref._site_url).hostname
                    if src_doc.office_strings is None:
                        src_doc.office_strings = self.smart_parser_server_client.get_office_strings(sha256)
                    case = TPredictionCase(self.office_ml_model, sha256, web_domain,-1, src_doc.office_strings)
                    predict_cases.append(case)
        predicted_office_ids = self.office_ml_model.predict(predict_cases)
        max_weights = defaultdict(float)
        for case, (office_id, weight) in zip(predict_cases, predicted_office_ids):
            if max_weights[case.sha256] > weight:
                max_weights[case.sha256] = weight
                self.output_dlrobot_human.document_collection[case.sha256].calculated_office_id = office_id
                self.logger.debug("set file {} office_id={} (tensorflow)".format(sha256,
                                                                                      src_doc.calculated_office_id))

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

