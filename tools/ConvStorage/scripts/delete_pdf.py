import hashlib
import argparse
from ConvStorage.conversion_client import TDocConversionClient


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-pdf", dest='input_pdf', required=False)
    parser.add_argument("--input-sha256", dest='sha_256', required=False)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    if args.sha_256 is None:
        assert args.input_pdf.endswith(".pdf")
        with open(args.input_pdf, "rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest()
    else:
        sha256hash = args.sha_256

    conv_tasks = TDocConversionClient()
    if not conv_tasks.check_file_was_converted(sha256hash):
        print("cannot find in the conversion db with sha256{} ".format(sha256hash))
    else:
        print("delete item in  conversion db by sha256: {}".format(sha256hash))
        res = conv_tasks.delete_file(sha256hash)
        if not res:
            print ("conv_tasks.delete_file failed")

