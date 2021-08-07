from common.logging_wrapper import setup_logging
from predict_office.office_pool import TOfficePool
from predict_office.tensor_flow_office import TTensorFlowOfficeModel

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be train, test, toloka, split")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--all-pool", dest='all_pool')
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--dense-layer-size", dest='dense_layer_size', required=False, type=int, default=256)
    parser.add_argument("--toloka-pool", dest='toloka_pool', required=False)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    logger = setup_logging(log_file_name="predict_office.log")
    if args.action == "split":
        assert args.all_pool is not None
        model = TTensorFlowOfficeModel(logger, args.bigrams_path, args.model_folder,  args.row_count)
        TOfficePool(model, args.all_pool).split(args.train_pool, args.test_pool)
    else:
        model = TTensorFlowOfficeModel(logger, args.bigrams_path, args.model_folder,  args.row_count,
                                       args.train_pool, args.test_pool)
        if args.action == "train":
            model.train_tensorflow(args.dense_layer_size, args.epoch_count)
        elif args.action == "test":
            model.test()
        elif args.action == "toloka":
            model.toloka(args.toloka_pool)
        else:
            raise Exception("unknown action")


if __name__ == '__main__':
    main()

