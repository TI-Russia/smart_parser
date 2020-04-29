import hashlib
import argparse
from ConvStorage.conversion_client import TDocConversionClient


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
    conv_tasks = TDocConversionClient()
    try:
        conv_tasks.start_conversion_thread()
        for filepath in args.input:
            conv_tasks.start_conversion_task_if_needed(filepath, ".pdf", args.rebuild_pdf)
        conv_tasks.wait_doc_conversion_finished()
        for filepath in args.input:
            download_converted_file_for(conv_tasks, filepath)
    finally:
        conv_tasks.stop_conversion_thread()