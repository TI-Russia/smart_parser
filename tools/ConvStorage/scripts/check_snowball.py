from common.logging_wrapper import setup_logging
from ConvStorage.convert_storage import TConvertStorage
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-json", dest='db_json', required=True)
    parser.add_argument("--file-no", dest='file_no', type=int)
    parser.add_argument("--fix-file-offset", dest='fix_file_offset', action="store_true", default=False)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging(log_file_name="check_snowball.log")
    convert_storage = TConvertStorage(logger, args.db_json)
    convert_storage.check_storage(args.file_no, fix_file_offset=args.fix_file_offset)
