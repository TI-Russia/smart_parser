from ConvStorage.conv_storage_server import TConvertStorage
from common.logging_wrapper import setup_logging
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-folder", dest='db_input_files', default='db_input_files')
    parser.add_argument("--converted-folder", dest='db_converted_files', default='db_converted_files')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    parser.add_argument("--forget-old-data", dest='forget_old_data', default=False,
                        action="store_true", help="if specified then the old converted_file_storage.json would be ignored")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging(log_file_name="recreate_db.log", append_mode=True)
    if args.forget_old_data:
        TConvertStorage.create_empty_db(args.db_input_files,  args.db_converted_files, args.output_file)
    storage = TConvertStorage(logger, args.output_file)
    storage.register_missing_files()
    storage.save_database()

