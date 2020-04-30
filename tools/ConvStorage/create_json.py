import os
import argparse
from conv_storage_server import find_new_files_and_add_them_to_json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", dest='directory', default='files')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if not os.path.exists(args.directory):
        os.mkdir(args.directory)
    find_new_files_and_add_them_to_json(None, args.directory, args.output_file)

