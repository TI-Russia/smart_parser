from common.logging_wrapper import setup_logging
from common.file_storage import TFileStorage

import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-fast", dest='fail_fast', default=False)
    parser.add_argument("data_folder")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging(log_file_name="check_storage.log")
    file_storage = TFileStorage(logger, args.   data_folder, read_only=True)
    if not file_storage.check_storage(args.fail_fast):
        sys.exit(1)
