import time

from dlrobot_human.dlrobot_human_dbm import TDlrobotHumanFileDBM
from dlrobot_human.input_document import TWebReference, TSourceDocument
from predict_office.tensor_flow_model import TTensorFlowOfficeModel
from predict_office.office_pool import TOfficePool
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeInMemory
from office_db.rubrics import TOfficeRubrics
from predict_office.read_office_from_title import TOfficeFromTitle, TTitleParseResult
from office_db.web_site_list import TDeclarationWebSiteList
from office_db.russia import RUSSIA

import os
import json
import argparse
import sys


class TAdhocRuleResults:
    def __init__(self, cases, max_freq_heuristics, single_web_site, parse_title, first_web_site_evil, no_title):
        self.cases = cases
        self.max_freq_heuristics = max_freq_heuristics
        self.single_web_site = single_web_site
        self.parse_title = parse_title
        self.first_web_site_evil = first_web_site_evil
        self.no_title = no_title


class TOfficePredictor:
    default_ml_model_path = os.path.join(os.path.dirname(__file__), "../model")

    @staticmethod
    def parse_args(args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--dlrobot-human-path", dest='dlrobot_human_path', required=True)
        parser.add_argument("--office-model-path", dest='office_model_path', required=False,
                            default=TOfficePredictor.default_ml_model_path)
        parser.add_argument("--disable-ml", dest='enable_ml', required=False, default=True,
                            action="store_false")
        parser.add_argument("--max-failures-count", dest='max_failures_count', required=False, default=100,
                            type=int)
        return parser.parse_args(args=args)

    def __init__(self, args):
        self.logger = setup_logging(log_file_name="predict_office.log")
        self.dlrobot_human_path = args.dlrobot_human_path
        self.dlrobot_human = TDlrobotHumanFileDBM(self.dlrobot_human_path)
        self.dlrobot_human.open_write_mode()
        self.enable_ml = args.enable_ml
        sp_args = TSmartParserCacheClient.parse_args([])
        self.smart_parser_server_client = TSmartParserCacheClient(sp_args, self.logger)
        model_path = args.office_model_path
        self.max_failures_count = args.max_failures_count
        assert (os.path.exists(model_path))
        bigrams_path = os.path.join(model_path, "office_ngrams.txt")
        ml_model_path = os.path.join(model_path, "model")
        self.office_ml_model = TTensorFlowOfficeModel(self.logger, bigrams_path, ml_model_path, create_model=False)
        self.regional_tax_offices = self.build_regional_tax_offices()
        self.web_sites = TDeclarationWebSiteList(self.logger, RUSSIA.offices_in_memory)
        self.title_parser = TOfficeFromTitle(self.logger, web_sites=self.web_sites)
        self.src_doc_to_rule_results = dict()

    def build_regional_tax_offices(self):
        o: TOfficeInMemory
        tax_offices = dict()
        for o in RUSSIA.iterate_offices():
            if o.rubric_id == TOfficeRubrics.Tax:
                tax_offices[o.region_id] = o.office_id
        assert len(tax_offices) > 0
        return tax_offices

    def set_office_id(self, sha256, src_doc: TSourceDocument, office_id, method_name: str):
        old_office_id = src_doc.calculated_office_id
        if old_office_id is None or office_id == old_office_id:
            self.logger.debug("set file {} office_id={} ({} )".format(
                sha256, office_id, method_name))
        else:
            self.logger.info("change office_id from {} to {} for file {} , ({})".format( \
                old_office_id, office_id, sha256, method_name))
        src_doc.calculated_office_id = office_id
        self.dlrobot_human.update_source_document(sha256, src_doc)

    def predict_tax_office(self, sha256, src_doc: TSourceDocument):
        web_ref: TWebReference
        for web_ref in src_doc.web_references:
            if web_ref._site_url.endswith("service.nalog.ru"):
                if src_doc.region_id is None:
                    smart_parser_json = self.smart_parser_server_client.retrieve_json_by_sha256(sha256)
                    if smart_parser_json is None:
                        return False
                    props = smart_parser_json.get('document_sheet_props')
                    if props is None or len(props) == 0 or 'url' not in props[0]:
                        return False
                    url = props[0]['url']
                    region_str = url[:url.find('.')]
                    if not region_str.isdigit():
                        return False
                    src_doc.region_id = int(region_str)

                office_id = self.regional_tax_offices.get(src_doc.region_id)
                if office_id is not None:
                    self.set_office_id(sha256, src_doc, office_id, "regional tax office")
                    return True
        return False

    # all sites are ascribed to the same office
    def single_web_site(self, src_doc):
        r: TWebReference
        offices = set()
        for r in src_doc.web_references:
            if r.get_site_url():
                site_info = self.web_sites.search_url(r.get_site_url())
                if site_info is not None:
                    offices.add(site_info.parent_office.office_id)
        if len(offices) == 1:
            return list(offices)[0]
        return None

    #Take the first office, that is a very bad solution. This is done to make the whole thing work.
    # In future we hope to get rid of this solution by adding anchor texts analysis  or moro sophisticated title parsing
    def predict_by_first_web_site(self, case: TPredictionCase, src_doc):
        r: TWebReference
        min_crawl_epoch = time.time()
        office_id = None
        for r in src_doc.web_references:
            if 0 < r.crawl_epoch < min_crawl_epoch:
                site_info = self.web_sites.search_url(r.get_site_url())
                if site_info is not None:
                    min_crawl_epoch = r.crawl_epoch
                    office_id = site_info.parent_office.office_id
        return office_id

    def predict_by_title(self, case: TPredictionCase, src_doc):
        if not TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings):
            parse_result: TTitleParseResult
            parse_result = self.title_parser.parse_title(case)
            if parse_result is not None and parse_result.weight > 0.5:
                return parse_result.office.office_id

    def predict_by_post_ml_rules(self, case: TPredictionCase, src_doc):
        rule_results: TAdhocRuleResults
        rule_results = self.src_doc_to_rule_results[case.sha256]
        if rule_results.parse_title:
            office_id = rule_results.parse_title
            message = "title_parser office_id={}".format(office_id)
            if rule_results.single_web_site != office_id and rule_results.single_web_site is not None:
                message += " contradicts to single_web_site_office_id={}".format(rule_results.single_web_site)
            self.set_office_id(case.sha256, src_doc, office_id, message)
        elif rule_results.single_web_site is not None:
            self.set_office_id(case.sha256, src_doc, rule_results.single_web_site, "parent_office ")
        elif rule_results.first_web_site_evil is not None:
            self.set_office_id(case.sha256, src_doc, rule_results.first_web_site_evil, "first_web_site_evil ")

    def predict_offices_by_ml_and_post_ml_rules(self,  cases, min_ml_weight=0.99):
        TOfficePool.write_pool(cases, "cases_to_predict_dump.txt")
        predicted_office_ids = self.office_ml_model.predict_by_portions(cases)
        cases_filtered = ( (weight, office_id, case.sha256) \
                          for case, (office_id, weight) in zip(cases, predicted_office_ids) \
                          if weight >= min_ml_weight)
        already = set()
        for weight, office_id, sha256 in sorted(cases_filtered, reverse=True):
            if sha256 in already:
                continue
            already.add(sha256)
            src_doc = self.dlrobot_human.get_document(sha256)
            self.set_office_id(sha256, src_doc, office_id, "tensorflow weight={}".format(weight))

        for case in cases:
            if case.sha256 not in already:
                # set by hand
                src_doc = self.dlrobot_human.get_document(case.sha256)
                self.predict_by_post_ml_rules(case, src_doc)
                already.add(case.sha256)

    def update_office_string(self, sha256, src_doc):
        try:
            src_doc.office_strings = json.dumps(self.smart_parser_server_client.get_office_strings(sha256),
                                                ensure_ascii=False)
        except json.JSONDecodeError as err:
            self.logger.error("bad json for sha256={} err={}".format(sha256, str(err)))
            raise
        #real write to dbm
        self.dlrobot_human.update_source_document(sha256, src_doc)

    def get_office_using_max_freq_heuristics(self, sha256, src_doc):
        web_ref: TWebReference
        for web_ref in src_doc.web_references:
            office = self.office_ml_model.office_index.web_sites.get_office(web_ref._site_url)
            if office is not None:
                return office.office_id

    def calc_features(self, sha256, src_doc) -> TAdhocRuleResults:
        web_ref: TWebReference
        cases = list()
        for web_ref in src_doc.web_references:
            case = TPredictionCase.build_from_web_reference(self.office_ml_model.office_index, sha256,
                                                     src_doc, web_ref, true_office_id=None)
            cases.append(case)
        if len(cases) == 0:
            return None
        return TAdhocRuleResults(
            cases=cases,
            max_freq_heuristics=self.get_office_using_max_freq_heuristics(sha256, src_doc),
            single_web_site=self.single_web_site(src_doc),
            parse_title=self.predict_by_title(cases[0], src_doc),
            first_web_site_evil=self.predict_by_first_web_site(cases[0], src_doc),
            no_title=TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings)
        )

    def predict_office(self):
        cases_for_ml_predict = list()
        src_doc: TSourceDocument
        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if len(src_doc.decl_references) > 0:
                self.set_office_id(sha256,src_doc, src_doc.decl_references[0].office_id, "declarator")
                if src_doc.office_strings is None:
                    if src_doc.can_be_used_for_declarator_train():
                        # for train generation
                        self.update_office_string(sha256, src_doc)
            elif self.predict_tax_office(sha256, src_doc):
                pass
            else:
                if not self.enable_ml or src_doc.office_strings is None:
                    self.update_office_string(sha256, src_doc)
                rule_results = self.calc_features(sha256, src_doc)
                if rule_results is None:
                    self.logger.debug("no way to set office id")
                    continue
                self.src_doc_to_rule_results[sha256] = rule_results
                if not self.enable_ml or rule_results.no_title:
                    if rule_results.single_web_site == rule_results.parse_title and rule_results.parse_title is not None:
                        message = "parse_title and single_web_site"
                        if rule_results.max_freq_heuristics is not None and rule_results.parse_title != rule_results.max_freq_heuristics:
                            message = " contradicts to max_freq_heuristics(office_id={})".format(rule_results.max_freq_heuristics)
                        self.set_office_id(sha256, src_doc, rule_results.parse_title, message)
                    else:
                        self.set_office_id(sha256, src_doc, rule_results.max_freq_heuristics, "max freq heuristics")
                else:
                    cases_for_ml_predict.extend(rule_results.cases)
        if len(cases_for_ml_predict) > 0:
            self.predict_offices_by_ml_and_post_ml_rules(cases_for_ml_predict)

    def check(self):
        files_without_office_id = 0
        files_without_json_and_office_id = 0
        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if src_doc.calculated_office_id is None:
                if TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings):
                    files_without_json_and_office_id += 1
                    self.logger.error("website: {}, file {} has no office and no json".format(src_doc.get_web_site(), sha256))
                else:
                    self.logger.error("website: {}, file {} has no office".format(src_doc.get_web_site(), sha256))
                    files_without_office_id += 1

        self.logger.info("all files count = {}, files_without_office_id = {} files_without_json_and_office_id = {}".format(
                self.dlrobot_human.get_documents_count(), files_without_office_id, files_without_json_and_office_id))
        if files_without_office_id > self.max_failures_count:
            error = "too many files (more than > {}) without offices".format(self.max_failures_count)
            self.logger.error(error)
            raise Exception(error)

    def write(self):
        self.dlrobot_human.close_db()


def main():
    predictor = TOfficePredictor(TOfficePredictor.parse_args(sys.argv[1:]))
    predictor.predict_office()
    predictor.check()
    predictor.write()


if __name__ == "__main__":
    main()
