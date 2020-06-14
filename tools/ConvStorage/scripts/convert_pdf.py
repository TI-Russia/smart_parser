import hashlib
import argparse
import sys
import os
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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='+')
    parser.add_argument("--rebuild", dest='rebuild_pdf', action="store_true", default=False)
    parser.add_argument("--conversion-timeout", dest='conversion_timeout', type=int, default=60*30)
    parser.add_argument("--conversion-server", dest='conversion_server', required=False)
    return parser.parse_args()


def send_files(args, logger, conv_tasks):
    sent_files = set()
    for filepath in args.input:
        _, extension = os.path.splitext(filepath)
        if conv_tasks.start_conversion_task_if_needed(filepath, extension.lower(), args.rebuild_pdf):
            logger.debug("send {}".format(filepath))
            sent_files.add(filepath)
    return sent_files


def receive_files(logger, conv_tasks, sent_files):
    errors_count = 0
    for filepath in sent_files:
        logger.debug("download docx for {}".format(filepath))
        with open(filepath, "rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest()
        outfile = filepath + ".docx"
        if conv_tasks.retrieve_document(sha256hash, outfile):
            logger.debug("save {}".format(outfile))
        else:
            logger.error("cannot download docx for file {}".format(filepath))
            errors_count += 1
    return errors_count == 0


def main(args, logger):
    if args.conversion_server is not None:
        TDocConversionClient.DECLARATOR_CONV_URL = args.conversion_server
    conv_tasks = TDocConversionClient(logger)
    conv_tasks.start_conversion_thread()

    try:
        sent_files = send_files(args, logger, conv_tasks)
        if len(sent_files) > 0:
            conv_tasks.wait_doc_conversion_finished(args.conversion_timeout)
        else:
            logger.debug("stop conversion finished")
            conv_tasks.stop_conversion_thread()
    except Exception as exp:
        logger.error("exception: {}, stop_conversion_thread".format(exp))
        conv_tasks.stop_conversion_thread()
    if not receive_files(logger, conv_tasks, sent_files):
        return 1
    return 0


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging()
    exit_code = main(args, logger)
    sys.exit(exit_code)