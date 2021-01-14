import sys
import logging
from ConvStorage.conversion_client import TDocConversionClient


def setup_logging():
    logger = logging.getLogger("convert_pdf")
    logger.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler("convert_pdf.log", encoding="utf8")
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
    client = TDocConversionClient(TDocConversionClient.parse_args(sys.argv[1:]),  logger)
    client.start_conversion_thread()
    exit_code = client.process_files()
    sys.exit(exit_code)