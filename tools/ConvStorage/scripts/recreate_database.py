import argparse
from ConvStorage.conv_storage_server import TConvertStorage
import logging

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-folder", dest='db_input_files', default='db_input_files')
    parser.add_argument("--converted-folder", dest='db_converted_files', default='db_converted_files')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    TConvertStorage.create_empty_db(args.output_file, args.db_input_files,  args.db_converted_files)
    storage = TConvertStorage(logging.getLogger("recreate_db"), args.output_file)
    storage.recreate_database()
    storage.save_database()

