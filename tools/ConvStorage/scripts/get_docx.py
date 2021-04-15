from ConvStorage.conversion_client import TDocConversionClient
from common.logging_wrapper import setup_logging
import sys

if __name__ == '__main__':
    logger = setup_logging(log_file_name="get_docx.log")
    client = TDocConversionClient(TDocConversionClient.parse_args(sys.argv[1:]),  logger)
    for sha256 in client.args.input:
        output_file_path = sha256 + '.docx'
        if client.retrieve_document(sha256, output_file_path, verbose=True):
            logger.info("create {}".format(output_file_path))

