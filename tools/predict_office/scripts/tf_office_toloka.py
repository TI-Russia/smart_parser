from common.logging_wrapper import setup_logging
from predict_office.tensor_flow_model import TTensorFlowOfficeModel

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--toloka-output-pool", dest='toloka_pool', required=False)
    parser.add_argument("--format", dest='format', default=1, type=int)
    return parser.parse_args()


def main():
    logger = setup_logging(log_file_name="predict_office_toloka.log")
    args = parse_args()
    model = TTensorFlowOfficeModel(logger, args.bigrams_path, args.model_folder, create_model=False,
                                   work_pool_path=args.test_pool)
    model.toloka(args.toloka_pool, format=args.format)


if __name__ == "__main__":
    main()
