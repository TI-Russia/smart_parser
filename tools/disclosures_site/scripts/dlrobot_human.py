from declarations.input_json import TSourceDocument, TDlrobotHumanFileDBM, TWebReference
from predict_office.office_pool import TOfficePool
from predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from predict_office.office_index import TOfficePredictIndex

import argparse
import json
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be stats, select, "
                                                        "print_sha256, print_web_sites, "
                                                        "delete, to_utf8, titles, check_office, to_json,"
                                                        " build_office_train_set, print_office_id, rebuild_ml_pool")
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--sha256-list-file", dest='sha256_list_file', required=False)
    parser.add_argument("--sha256", dest='sha256', required=False)
    parser.add_argument("--output-predict-office-pool", dest='output_predict_office_pool_path', required=False)
    parser.add_argument("--input-predict-office-pool", dest='input_predict_office_pool_path', required=False)
    return parser.parse_args()


class TDlrobotHumanManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging(logger_name="dlrobot_human")
        self.dlrobot_human = TDlrobotHumanFileDBM(self.args.input_file)
        self.dlrobot_human.open_db_read_only()
        if self.args.action in {"check_office", "build_office_train_set", "rebuild_ml_pool"}:
            default_path = os.path.join(os.path.dirname(__file__), "../predict_office/model/office_ngrams.txt")
            self.office_index = TOfficePredictIndex(self.logger, default_path)
            self.office_index.read()
        else:
            self.office_index = None

    def print_web_sites(self):
        value: TSourceDocument
        for key, value in self.dlrobot_human.get_all_documents():
            print("{}\t{}".format(key, value.get_web_site()))

    def read_sha256_list(self):
        if self.args.sha256_list_file is not None:
            sha_set = set()
            with open(self.args.sha256_list_file) as inp:
                for x in inp:
                    sha_set.add(x.strip())
            return sha_set
        else:
            assert self.args.sha256 is not None
            return {self.args.sha256}

    def select_or_delete_by_sha256(self, output_file, select=True):
        sha256_list = self.read_sha256_list()
        assert self.args.output_file is not None

        new_dlrobot_human = TDlrobotHumanFileDBM(output_file)
        new_dlrobot_human.create_db()

        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if (sha256 in sha256_list) == select:
                new_dlrobot_human.update_source_document(sha256, src_doc)

        new_dlrobot_human.close_db()

    def to_utf8(self, output_file):
        new_dlrobot_human = TDlrobotHumanFileDBM(output_file)
        new_dlrobot_human.create_db()
        src_doc: TSourceDocument
        for key, src_doc in self.dlrobot_human.get_all_documents():
            src_doc.convert_refs_to_utf8()
            new_dlrobot_human.update_source_document(key, src_doc)
        new_dlrobot_human.close_db()

    def to_json(self):
        print(json.dumps(self.dlrobot_human.to_json(), indent=4, ensure_ascii=False))

    def check_office(self):
        pool = TOfficePool(self.logger)
        pool.read_cases(self.args.input_predict_office_pool_path)
        positive = 0
        negative = 0
        case: TPredictionCase
        for case in pool.pool:
            src_doc: TSourceDocument
            src_doc = self.dlrobot_human.get_document(case.sha256)
            if case.true_office_id == src_doc.calculated_office_id:
                self.logger.debug("positive case {} office_id={}".format(case.sha256, case.true_office_id))
                positive += 1
            else:
                self.logger.debug("negative case {} , office_id must be {} but predicted {}".format(
                    case.sha256, case.true_office_id, src_doc.calculated_office_id))
                negative += 1
        rec = {
            "positive_count": positive,
            "negative_count": negative,
            "precision": float(positive) / (negative + positive + 0.000000000001)
        }
        self.logger.info(json.dumps(rec))

    def get_predict_train_entries(self):
        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if src_doc.can_be_used_for_declarator_train() and \
                    not TSmartParserCacheClient.are_empty_office_strings(src_doc.office_strings) and \
                    src_doc.calculated_office_id is not None:
                yield sha256, src_doc, src_doc.calculated_office_id

    def get_generator_by_ml_pool(self):
        pool = TOfficePool(self.logger)
        pool.read_cases(self.args.input_predict_office_pool_path)
        for case in pool.pool:
            src_doc = self.dlrobot_human.get_document(case.sha256)
            yield case.sha256, src_doc, case.true_office_id

    def build_predict_office_ml_pool(self, entries_generator, output_pool_path):
        cases = list()
        src_doc: TSourceDocument
        for sha256, src_doc, true_office_id in entries_generator():
            web_ref: TWebReference
            found_web_domains = set()
            for web_ref in src_doc.web_references:
                case = TPredictionCase.build_from_web_reference(self.office_index, sha256, src_doc, web_ref,
                                                                true_office_id)
                if case.web_domain not in found_web_domains:
                    found_web_domains.add(case.web_domain)
                    cases.append(case)
        self.logger.info("write to {}".format(output_pool_path))
        TOfficePool.write_pool(cases, output_pool_path)

    def print_office_id(self):
        for key, src_doc in self.dlrobot_human.get_all_documents():
            print("{}\t{}".format(key, src_doc.calculated_office_id))

    def main(self):
        action = self.args.action
        if action == "print_web_sites":
            self.print_web_sites()
        elif action == "stats":
            print(json.dumps(self.dlrobot_human.get_stats(), indent=4))
        elif action == "check_office":
            self.check_office()
        elif action == "build_office_train_set":
            self.build_predict_office_ml_pool(self.get_predict_train_entries)
        elif action == "rebuild_ml_pool":
            self.build_predict_office_ml_pool(self.get_generator_by_ml_pool)
        elif action == "select" or args.action == "delete":
            self.select_or_delete_by_sha256(self.args.output_file, self.args.action == "select")
        elif action == "to_utf8":
            self.to_utf8(self.args.output_file)
        elif action == "to_json":
            self.to_json()
        elif action == "print_office_id":
            self.print_office_id()
        else:
            raise Exception("unknown action")


if __name__ == '__main__':
    manager = TDlrobotHumanManager()
    manager.main()


