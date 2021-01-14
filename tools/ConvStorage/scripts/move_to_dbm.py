import json
import os
import logging
import argparse
from  ConvStorage.convert_storage import TConvertStorage


def setup_logging():
    logger = logging.getLogger("move_to_dbm")
    logger.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler("move_to_dbm.log", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-project", dest='input_project')
    parser.add_argument("--output-project", dest='output_project')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging()
    TConvertStorage.create_empty_db(args.output_project, "db_input_files", "db_converted_files")
    out_storage = TConvertStorage(logger, args.output_project)

    input_json = None
    with open(args.input_project, "r") as inp:
        input_json = json.load(inp)
    input_folder = os.path.join( os.path.dirname(args.input_project), input_json["input_folder"])
    converted_folder = os.path.join(os.path.dirname(args.input_project), input_json["converted_folder"])

    for sha256, file_info in input_json['files'].items():
        logger.debug(sha256)
        input_file = os.path.join(input_folder, sha256  + ".pdf")
        if not os.path.exists(input_file):
            logger.error("cannot find {}".format(input_file))
            continue
        converted_file = os.path.join(converted_folder, sha256  + ".pdf.docx")
        if not os.path.exists(converted_file):
            logger.error("cannot find {}".format(converted_file))
            continue

        converter_id = file_info.get('c', "word")
        access = file_info.get('a')
        if access is not None:
            out_storage.register_access_request(sha256, timestamp=access*60*60*24)
        out_storage.save_input_file(input_file, delete_file=False)
        out_storage.save_converted_file(converted_file, sha256, converter_id, delete_file=False)

    out_storage.close_storage()
    logger.debug("all done")