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
                                                        "print_sha256, print_web_sites, create_sample, "
                                                        "delete, to_utf8, titles, check_office, to_json,"
                                                        " build_office_train_set, print_office_id, rebuild_ml_pool, "
                        "unknown_office_uniq_website_pool")
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--sha256-list-file", dest='sha256_list_file', required=False)
    parser.add_argument("--sha256", dest='sha256', required=False)
    parser.add_argument("--input-predict-office-pool", dest='input_predict_office_pool_path', required=False)
    parser.add_argument("--output-predict-office-pool", dest='output_predict_office_pool_path', required=False)
    return parser.parse_args()


class TDlrobotHumanManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging(logger_name="dlrobot_human")
        self.dlrobot_human = TDlrobotHumanFileDBM(self.args.input_file)
        self.dlrobot_human.open_db_read_only()
        if self.args.action in {"check_office", "build_office_train_set"} or self.args.action.endswith('_pool'):
            default_path = os.path.join(os.path.dirname(__file__), "../predict_office/model/office_ngrams.txt")
            self.office_index = TOfficePredictIndex(self.logger, default_path)
            self.office_index.read()
        else:
            self.office_index = None

    def print_web_sites(self):
        value: TSourceDocument
        for key, value in self.dlrobot_human.get_all_documents():
            print("{}\t{}".format(key, value.get_web_site()))

    def has_sha256_filters(self):
        return self.args.sha256_list_file is not None or self.args.sha256 is not None

    def build_sha256_list(self):
        assert self.has_sha256_filters()
        if self.args.sha256_list_file is not None:
            sha_set = set()
            with open(self.args.sha256_list_file) as inp:
                for x in inp:
                    sha_set.add(x.strip())
            return sha_set
        else:
            return {self.args.sha256}

    def select_by_sha256(self):
        sha256_list = self.build_sha256_list()
        assert self.args.output_file is not None

        new_dlrobot_human = TDlrobotHumanFileDBM(self.args.output_file)
        new_dlrobot_human.create_db()

        for sha256 in sha256_list:
            src_doc = self.dlrobot_human.get_document(sha256)
            new_dlrobot_human.update_source_document(sha256, src_doc)

        new_dlrobot_human.close_db()

    def delete_by_sha256(self):
        sha256_list = self.build_sha256_list()
        assert self.args.output_file is not None

        new_dlrobot_human = TDlrobotHumanFileDBM(self.args.output_file)
        new_dlrobot_human.create_db()

        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if sha256 not in sha256_list:
                new_dlrobot_human.update_source_document(sha256, src_doc)

        new_dlrobot_human.close_db()

    def to_utf8(self):
        new_dlrobot_human = TDlrobotHumanFileDBM(self.args.output_file)
        new_dlrobot_human.create_db()
        src_doc: TSourceDocument
        for key, src_doc in self.dlrobot_human.get_all_documents():
            src_doc.convert_refs_to_utf8()
            new_dlrobot_human.update_source_document(key, src_doc)
        new_dlrobot_human.close_db()

    def to_json(self):
        if self.has_sha256_filters():
            self.args.output_file = "tmp.dbm"
            self.select_by_sha256()
            tmp_db = TDlrobotHumanFileDBM(self.args.output_file)
            tmp_db.open_db_read_only()
            js = tmp_db.to_json()
            tmp_db.close_db()
            os.unlink(self.args.output_file)
        else:
            js = self.dlrobot_human.to_json()

        print(json.dumps(js, indent=4, ensure_ascii=False))

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

    def get_unknown_office_uniq_website(self):
        websites = set()
        for sha256, src_doc in self.dlrobot_human.get_all_documents():
            if src_doc.calculated_office_id is not None:
                continue
            if src_doc.office_strings is None or len(json.loads(src_doc.office_strings).get('title', "")) < 10:
                continue
            web_site = src_doc.get_web_site()
            if web_site in websites:
                continue
            websites.add(web_site)
            yield sha256, src_doc, src_doc.calculated_office_id

    def get_generator_by_source_ml_pool(self):
        #pool = TOfficePool(self.logger)
        #pool.read_cases(self.args.input_predict_office_pool_path)
        with open(self.args.input_predict_office_pool_path) as inp:
            for line in inp:
                sha256, office_id = line.strip().split("\t")
                src_doc = self.dlrobot_human.get_document(sha256)
                yield sha256, src_doc, int(office_id)

    def build_predict_office_ml_pool(self, entries_generator):
        cases = list()
        src_doc: TSourceDocument
        input_lines_cnt = 0
        for sha256, src_doc, true_office_id in entries_generator():
            web_ref: TWebReference
            found_web_domains = set()
            input_lines_cnt += 1
            for web_ref in src_doc.web_references:
                self.logger.debug("process {}, sha256 = {}".format(web_ref.url, sha256))
                case = TPredictionCase.build_from_web_reference(self.office_index, sha256, src_doc, web_ref,
                                                                true_office_id)
                if case.web_domain not in found_web_domains:
                    found_web_domains.add(case.web_domain)
                    cases.append(case)
        self.logger.info("process {} lines from the input file".format(input_lines_cnt))
        self.logger.info("write {} lines to {}".format(len(cases), self.args.output_predict_office_pool_path))
        TOfficePool.write_pool(cases, self.args.output_predict_office_pool_path)

    def print_office_id(self):
        for key, src_doc in self.dlrobot_human.get_all_documents():
            print("{}\t{}".format(key, src_doc.calculated_office_id))

    def print_sha256(self):
        for key in self.dlrobot_human.get_all_keys():
            print(key)

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
            self.build_predict_office_ml_pool(self.get_generator_by_source_ml_pool)
        elif action == "unknown_office_uniq_website_pool":
            self.build_predict_office_ml_pool(self.get_unknown_office_uniq_website)
        elif action == "select":
            self.select_by_sha256()
        elif action == "delete":
            self.delete_by_sha256()
        elif action == "to_utf8":
            self.to_utf8()
        elif action == "to_json":
            self.to_json()
        elif action == "print_office_id":
            self.print_office_id()
        elif action == "print_sha256":
            self.print_sha256()
        else:
            raise Exception("unknown action")


if __name__ == '__main__':
    manager = TDlrobotHumanManager()
    manager.main()


