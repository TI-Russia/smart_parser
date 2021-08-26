from declarations.input_json import TSourceDocument, TDlrobotHumanFileDBM, TWebReference
from disclosures_site.predict_office.tensor_flow_model import TTensorFlowOfficeModel
from disclosures_site.predict_office.office_pool import TOfficePool
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from disclosures_site.predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from declarations.documents import OFFICES
from disclosures_site.declarations.offices_in_memory import TOfficeInMemory
from disclosures_site.declarations.rubrics import TOfficeRubrics

import os
import json
from django.core.management import BaseCommand


class TOfficePredictor:
    default_ml_model_path = os.path.join(os.path.dirname(__file__), "../../model")

    def __init__(self, options):
        self.logger = setup_logging(log_file_name="predict_office.log")
        self.dlrobot_human_path = options['dlrobot_human_path']
        self.dlrobot_human = TDlrobotHumanFileDBM(self.dlrobot_human_path)
        self.dlrobot_human.open_write_mode()
        self.enable_ml = options.get('enable_ml', True)
        sp_args = TSmartParserCacheClient.parse_args([])
        self.smart_parser_server_client = TSmartParserCacheClient(sp_args, self.logger)
        model_path = options.get('office_model_path', TOfficePredictor.default_ml_model_path)
        assert (os.path.exists(model_path))
        bigrams_path = os.path.join(model_path, "office_ngrams.txt")
        ml_model_path = os.path.join(model_path, "model")
        self.office_ml_model = TTensorFlowOfficeModel(self.logger, bigrams_path, ml_model_path)
        self.regional_tax_offices = self.build_regional_tax_offices()

    def build_regional_tax_offices(self):
        o: TOfficeInMemory
        tax_offices = dict()
        for o in OFFICES.offices.values():
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

    def predict_offices_by_ml(self,  cases, min_ml_weight=0.99):
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
                # set by the old method
                src_doc = self.dlrobot_human.get_document(case.sha256)
                self.get_office_using_max_freq_heuristics(case.sha256, src_doc)
                already.add(case.sha256)

    def update_office_string(self, sha256, src_doc):
        src_doc.office_strings = json.dumps(self.smart_parser_server_client.get_office_strings(sha256),
                                            ensure_ascii=False)
        #real write to dbm
        self.dlrobot_human.update_source_document(sha256, src_doc)

    def get_office_using_max_freq_heuristics(self, sha256, src_doc):
        web_ref: TWebReference
        for web_ref in src_doc.web_references:
            web_site = self.office_ml_model.office_index.web_sites.get_web_site(web_ref._site_url)
            if web_site is not None:
                self.set_office_id(sha256, src_doc, web_site.calculated_office_id, "max freq heuristics")
                return

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
                if not self.enable_ml or TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings):
                    self.get_office_using_max_freq_heuristics(sha256, src_doc)
                else:
                    web_ref: TWebReference
                    for web_ref in src_doc.web_references:
                        case = TPredictionCase.build_from_web_reference(self.office_ml_model.office_index,sha256,
                                                                 src_doc, web_ref, true_office_id=None)
                        cases_for_ml_predict.append(case)
        if len(cases_for_ml_predict) > 0:
            self.predict_offices_by_ml(cases_for_ml_predict)

    def check(self):
        files_without_office_id = 0

        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if src_doc.calculated_office_id is None:
                self.logger.error("website: {}, file {} has no office".format(src_doc.get_web_site(), sha256))
                files_without_office_id += 1

        self.logger.info("all files count = {}, files_without_office_id = {}".format(
                self.dlrobot_human.get_documents_count(), files_without_office_id))
        if files_without_office_id > 100:
            error = "too many files without offices"
            self.logger.error(error)
            raise Exception(error)

    def write(self):
        self.dlrobot_human.close_db()


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument("--dlrobot-human-path", dest='dlrobot_human_path', required=True)
        parser.add_argument("--office-model-path", dest='office_model_path', required=False,
                            default=TOfficePredictor.default_ml_model_path)
        parser.add_argument("--disable-ml", dest='enable_ml', required=False, default=True,
                            action="store_false")

    def handle(self, *args, **options):
        predictor = TOfficePredictor(options)
        predictor.predict_office()
        predictor.check()
        predictor.write()


