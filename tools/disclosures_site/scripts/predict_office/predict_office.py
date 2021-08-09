from declarations.input_json import TSourceDocument, TDlrobotHumanFile, TWebReference
from disclosures_site.predict_office.tensor_flow_office import TTensorFlowOfficeModel
from disclosures_site.predict_office.office_pool import TOfficePool
from common.urllib_parse_pro import urlsplit_pro
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from disclosures_site.predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from web_site_db.web_sites import TDeclarationWebSiteList

import sys
import argparse
import os
import json
from collections import defaultdict
import gc



class TOfficePredicter:

    @staticmethod
    def parse_args(arg_list):
        default_ml_model_path = os.path.join(os.path.dirname(__file__), "../../predict_office/model")
        parser = argparse.ArgumentParser()
        parser.add_argument("--dlrobot-human-path", dest='dlrobot_human_path', required=True)
        parser.add_argument("--office-model-path", dest='office_model_path', required=False,
                            default=default_ml_model_path)
        return parser.parse_args(arg_list)

    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(log_file_name="predict_office.log")
        self.dlrobot_human = TDlrobotHumanFile(args.dlrobot_human_path)
        sp_args = TSmartParserCacheClient.parse_args([])
        self.smart_parser_server_client = TSmartParserCacheClient(sp_args, self.logger)
        bigrams_path = os.path.join(args.office_model_path, "office_ngrams.txt")
        ml_model_path = os.path.join(args.office_model_path, "model")
        self.office_ml_model = TTensorFlowOfficeModel(self.logger, bigrams_path, ml_model_path)
        self.web_sites = TDeclarationWebSiteList(self.logger)
        self.web_sites.load_from_disk()

    def set_office_id(self, sha256, src_doc: TSourceDocument, office_id, method_name: str):
        old_office_id = src_doc.calculated_office_id
        if old_office_id is None or office_id == old_office_id:
            self.logger.debug("set file {} office_id={} ({} )".format(
                sha256, office_id, method_name))
        else:
            self.logger.info("change office_id from {} to {} for file {} , ({})".format( \
                old_office_id, office_id, sha256, method_name))
        src_doc.calculated_office_id = office_id

    def predict_office_deterministic_web_domain(self, sha256, src_doc: TSourceDocument):
        web_ref: TWebReference
        for web_ref in src_doc.web_references:
            web_domain = urlsplit_pro(web_ref._site_url).hostname
            office_id = self.office_ml_model.get_office_id_by_deterministic_web_domain(web_domain)
            if office_id is not None:
                self.set_office_id(sha256, src_doc, office_id, "deterministic web domain {}".format(web_domain))
                return True
        return False

    def predict_office(self, intermediate_save=False):
        predict_cases = list()
        src_doc: TSourceDocument
        for sha256, src_doc in self.dlrobot_human.document_collection.items():
            if len(src_doc.decl_references) > 0:
                self.set_office_id(sha256,src_doc, src_doc.decl_references[0].office_id, "declarator")
            elif self.predict_office_deterministic_web_domain(sha256, src_doc):
                pass
            else:
                if src_doc.office_strings is None:
                    src_doc.office_strings = json.dumps(self.smart_parser_server_client.get_office_strings(sha256),
                                                        ensure_ascii=False)
                if TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings):
                    web_ref: TWebReference
                    for web_ref in src_doc.web_references:
                        web_site = self.web_sites.get_web_site(web_ref._site_url)
                        if web_site is not None:
                            self.set_office_id(sha256, src_doc, web_site.calculated_office_id, "max freq heuristics")
                            break
                else:
                    web_ref: TWebReference
                    for web_ref in src_doc.web_references:
                        web_domain = urlsplit_pro(web_ref._site_url).hostname
                        case = TPredictionCase(self.office_ml_model, sha256, web_domain,
                                               office_strings=src_doc.office_strings)
                        predict_cases.append(case)

        if intermediate_save:
            self.write()
            self.logger.info("unload dlrobot_human to get more memory")
            del self.dlrobot_human
            gc.collect()

        self.office_ml_model.load_model()
        predicted_office_ids = self.office_ml_model.predict_by_portions(predict_cases)
        TOfficePool.write_pool(predict_cases, "cases_to_predict_dump.txt")
        if intermediate_save:
            self.dlrobot_human = TDlrobotHumanFile(args.dlrobot_human_path)

        max_weights = defaultdict(float)
        for case, (office_id, weight) in zip(predict_cases, predicted_office_ids):
            if max_weights[case.sha256] < weight:
                max_weights[case.sha256] = weight
                src_doc = self.dlrobot_human.document_collection[case.sha256]
                self.set_office_id(case.sha256, src_doc, office_id, "(tensorflow weight={})".format(weight))

    def check(self):
        files_without_office_id = 0

        for sha256, src_doc in self.dlrobot_human.document_collection.items():
            if src_doc.calculated_office_id is None:
                self.logger.error("website: {}, file {} has no office".format(src_doc.get_web_site(), sha256))
                files_without_office_id += 1

        self.logger.info("all files count = {}, files_without_office_id = {}".format(
                len(self.dlrobot_human.document_collection), files_without_office_id))
        if files_without_office_id > 100:
            error = "too many files without offices"
            self.logger.error(error)
            raise Exception(error)

    def write(self):
        self.dlrobot_human.write()


if __name__ == '__main__':
    args = TOfficePredicter.parse_args(sys.argv[1:])
    predicter = TOfficePredicter(args)
    predicter.predict_office(intermediate_save=True)
    predicter.check()
    predicter.write()


