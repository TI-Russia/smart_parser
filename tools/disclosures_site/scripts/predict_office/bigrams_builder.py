from predict_office.office_index import TOfficePredictIndex
from common.logging_wrapper import setup_logging

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    args = parser.parse_args()
    return args


def main():
    logger = setup_logging(log_file_name="build_office_bigrams.log")
    args = parse_args()
    index = TOfficePredictIndex(logger, args.bigrams_path)
    index.build()
    index.write()


if __name__ == '__main__':
    main()

