import hashlib
import argparse
import sys
import os
import logging
from ConvStorage.conversion_client import TDocConversionClient


def setup_logging(logger):
    logger.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='+')
    parser.add_argument("--rebuild", dest='rebuild_pdf', action="store_true", default=False)
    return parser.parse_args()


def download_converted_file_for(conv_tasks, filename):
    with open(filename, "rb") as f:
        sha256hash = hashlib.sha256(f.read()).hexdigest()
    outfile = filename + ".docx"
    if conv_tasks.retrieve_document(sha256hash, outfile):
        print ("save {}".format(outfile))


if __name__ == '__main__':
    args = parse_args()
    for filepath in args.input:
        if not os.path.exists(filepath):
            sys.stderr.write("{} does not exists\n".format(filepath))
            sys.exit(1)
    logger = logging.getLogger("stderr_logger")
    setup_logging(logger)
    conv_tasks = TDocConversionClient(logger)
    sent_files = set()
    try:
        conv_tasks.start_conversion_thread()
        for filepath in args.input:
            _, extension = os.path.splitext(filepath)
            if conv_tasks.start_conversion_task_if_needed(filepath, extension.lower(), args.rebuild_pdf):
                sys.stderr.write("send {}\n".format(filepath))
                sent_files.add(filepath)
        if len(sent_files) > 0:
            sys.stderr.write("wait conversion finished\n")
            conv_tasks.wait_doc_conversion_finished()
        else:
            conv_tasks.stop_conversion_thread()
    except Exception as exp:
        sys.stderr.write("exception: {}, stop_conversion_thread\n".format(exp))
        conv_tasks.stop_conversion_thread()

    for filepath in sent_files:
        sys.stderr.write("download docx for {}\n".format(filepath))
        download_converted_file_for(conv_tasks, filepath)
