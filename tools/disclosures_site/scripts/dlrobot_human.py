from declarations.input_json import TSourceDocument, TDlrobotHumanFile
from predict_office.office_pool import TOfficePool
from predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging

import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be stats, select, "
                                                        "print_sha256, print_web_sites, "
                                                        "delete, to_utf8, titles, check_office")
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--sha256-list-file", dest='sha256_list_file', required=False)
    parser.add_argument("--sha256", dest='sha256', required=False)
    parser.add_argument("--predict-test-pool", dest='predict_test_pool', required=False)
    return parser.parse_args()


def print_web_sites(dlrobot_human):
    value: TSourceDocument
    for key, value in dlrobot_human.get_all_documents():
        print("{}\t{}".format(key, value.get_web_site()))


def read_sha256_list(args):
    if args.sha256_list_file is not None:
        sha_set = set()
        with open(args.sha256_list_file) as inp:
            for x in inp:
                sha_set.add(x.strip())
        return sha_set
    else:
        assert args.sha256 is not None
        return {args.sha256}


def select_or_delete_by_sha256(dlrobot_human, sha256_list, output_file, select=True):
    new_dlrobot_human = TDlrobotHumanFile(output_file, read_db=False)

    for sha256, src_doc in dlrobot_human.get_all_documents():
        if (sha256 in sha256_list) == select:
            new_dlrobot_human.add_source_document(sha256, src_doc)

    new_dlrobot_human.write()


def to_utf8(dlrobot_human, output_file):
    new_dlrobot_human = TDlrobotHumanFile(output_file, read_db=False)
    src_doc: TSourceDocument
    for key, src_doc in dlrobot_human.get_all_documents():
        src_doc.convert_refs_to_utf8()
        new_dlrobot_human.add_source_document(key, src_doc)
    new_dlrobot_human.write()


class TDummyMlModel:
    def __init__(self, logger):
        self.logger = logger
        self.office_index = None


def check_office(logger, dlrobot_human, pool_path):
    ml_model = TDummyMlModel(logger)
    pool = TOfficePool(ml_model, file_name=pool_path)
    positive = 0
    negative = 0
    case: TPredictionCase
    for case in pool.pool:
        src_doc: TSourceDocument
        src_doc = dlrobot_human.get_document(case.sha256)
        if case.true_office_id == src_doc.calculated_office_id:
            logger.debug("positive case {} office_id={}".format(case.sha256, case.true_office_id))
            positive += 1
        else:
            logger.debug("negative case {} , office_id must be {} but predicted {}".format(
                case.sha256, case.true_office_id, src_doc.calculated_office_id))
            negative += 1
    rec = {
        "positive_count": positive,
        "negative_count": negative,
        "precision": float(positive) / (negative + positive + 0.000000000001)
    }
    logger.info(json.dumps(rec))

# print sha256 and office id
#cat dlrobot_human.json | jq -rc '.documents | to_entries[] | [.key, .value.office_id] | @tsv'

def main():
    args = parse_args()
    logger = setup_logging(logger_name="dlrobot_human")
    dlrobot_human = TDlrobotHumanFile(args.input_file)
    if args.action == "print_web_sites":
        print_web_sites(dlrobot_human)
    elif args.action == "stats":
        print(json.dumps(dlrobot_human.get_stats(), indent=4))
    elif args.action == "check_office":
        check_office(logger, dlrobot_human, args.predict_test_pool)
    elif args.action == "select" or args.action == "delete":
        sha_list = read_sha256_list(args.sha256_list_file)
        assert args.output_file is not None
        select_or_delete_by_sha256(dlrobot_human, sha_list, args.output_file, args.action == "select")
    elif args.action == "to_utf8":
        to_utf8(dlrobot_human, args.output_file)
    else:
        raise Exception("unknown action")


if __name__ == '__main__':
    main()


