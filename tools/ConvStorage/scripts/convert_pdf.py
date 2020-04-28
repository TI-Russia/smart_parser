import hashlib
import argparse
from ConvStorage.conversion_client import TDocConversionClient


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-pdf", dest='input_pdf', required=True)
    parser.add_argument("--rebuild", dest='rebuild_pdf', action="store_true", default=False)
    return parser.parse_args()


def process_file(conv_tasks, filename, rebuild):
    if rebuild:
        with open(filename, "rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest()
        if conv_tasks.check_file_was_converted(sha256hash):
            print("delete old converted file for {} {}".format(filename, sha256hash))
            conv_tasks.delete_file(sha256hash)
    conv_tasks.start_conversion_task_if_needed(filename, ".pdf")


if __name__ == '__main__':
    args = parse_args()
    assert args.input_pdf.endswith(".pdf")
    conv_tasks = TDocConversionClient()
    process_file(conv_tasks, args.input_pdf, args.rebuild_pdf)
    conv_tasks.wait_doc_conversion_finished()