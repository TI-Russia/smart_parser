import argparse
from ConvStorage.conv_storage_server import TConvertStorage
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-folder", dest='db_input_files', default='db_input_files')
    parser.add_argument("--converted-folder", dest='db_converted_files', default='db_converted_files')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    parser.add_argument("--forget-old-data", dest='forget_old_data', default=False,
                        action="store_true", help="if specified then the old converted_file_storage.json would be ignored")

    return parser.parse_args()


def setup_logging(logfilename="recreate_db.log"):
    logger = logging.getLogger("recreate_db")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging()
    if args.forget_old_data:
        TConvertStorage.create_empty_db(args.output_file, args.db_input_files,  args.db_converted_files)
    storage = TConvertStorage(logger, args.output_file)
    storage.register_missing_files()
    storage.save_database()

