from ConvStorage.conversion_client import TDocConversionClient
from common.logging_wrapper import setup_logging

import sys
import argparse
import os

def parse_args(arg_list):
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='*')
    parser.add_argument("--conversion-server", dest='conversion_server', required=False)
    TDocConversionClient.DECLARATOR_CONV_URL = os.environ.get('DECLARATOR_CONV_URL')  # reread for tests
    return parser.parse_args(arg_list)


if __name__ == '__main__':
    logger = setup_logging(log_file_name="get_docx.log", append_mode=True)
    client = TDocConversionClient(parse_args(sys.argv[1:]),  logger)
    for sha256 in client.args.input:
        output_file_path = sha256 + '.docx'
        if client.retrieve_document(sha256, output_file_path, verbose=True):
            logger.info("create {}".format(output_file_path))
        else:
            logger.info("cannot find {}".format(sha256))
            sys.exit(1)

