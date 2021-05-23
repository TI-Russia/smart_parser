from ConvStorage.conversion_client import TDocConversionClient
from common.logging_wrapper import setup_logging

import sys


if __name__ == '__main__':
    logger = setup_logging(log_file_name="convert_pdf.log")
    client = TDocConversionClient(TDocConversionClient.parse_args(sys.argv[1:]),  logger)
    client.start_conversion_thread()
    exit_code = client.process_files()
    sys.exit(exit_code)