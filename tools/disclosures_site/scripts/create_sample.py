from declarations.dlrobot_human_dbm import TDlrobotHumanFileDBM
from source_doc_http.source_doc_client import TSourceDocClient
from common.logging_wrapper import setup_logging
from smart_parser_http.smart_parser_client import TSmartParserCacheClient

import os
import random
import argparse
import shutil


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dbm-file", dest='input_file', required=True, help="dlrobot_human.dbm")
    parser.add_argument("--output-file", dest='output_file', default='sample.tar')
    parser.add_argument("--sample-size", dest='sample_size', default=1000, type=int)
    parser.add_argument("--income-year", dest='income_year', type=int, required=False)
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging("create_sample")
    dlrobot_human = TDlrobotHumanFileDBM(args.input_file)
    dlrobot_human.open_db_read_only()
    source_doc_client = TSourceDocClient(TSourceDocClient.parse_args([]))
    smart_parser_client = TSmartParserCacheClient(TSmartParserCacheClient.parse_args([]))
    logger.info("create population")

    tmp_folder = '/tmp/create_sample_sp'
    if os.path.exists(tmp_folder):
        shutil.rmtree(tmp_folder)
    logger.info("create directory {}".format(tmp_folder))
    os.mkdir(tmp_folder)
    population = list(dlrobot_human.get_all_keys())
    random.shuffle(population)

    logger.info("fetch files")
    found = set()
    for sha256 in population:
        logger.debug("get doc {}".format(sha256))
        file_data, file_extension = source_doc_client.retrieve_file_data_by_sha256(sha256)
        if file_data is None:
            logger.error("cannot get data for {}".format(sha256))
            continue

        if args.income_year is not None:
            smart_parser_json = smart_parser_client.retrieve_json_by_sha256(sha256)
            if smart_parser_json is None or len(smart_parser_json) == 0:
                logger.error("empty or invalid smart parser json for {}".format(sha256))
                continue
            src_doc = dlrobot_human.get_document(sha256)
            year = src_doc.calc_document_income_year(smart_parser_json)
            if year != args.income_year:
                logger.error("different year ({} != {})".format(year, args.income_year))
                continue
        found.add(sha256)
        file_path = os.path.join(tmp_folder, "{}{}".format(len(found) + 1, file_extension))
        with open(file_path, "wb") as outp:
            outp.write(file_data)
        if len(found) >= args.sample_size:
            break

    logger.info("found {} files".format(len(found)))
    output_file = os.path.abspath(args.output_file)
    cmd = "tar -C {} --create --file {} {}".format(
        os.path.dirname(tmp_folder),
        output_file,
        os.path.basename(tmp_folder))
    logger.info(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
