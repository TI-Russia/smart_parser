from common.logging_wrapper import setup_logging
from predict_office.tensor_flow_model import TTensorFlowOfficeModel
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False, default="model")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--dense-layer-size", dest='dense_layer_size', required=False, type=int, default=128)
    parser.add_argument("--batch-size", dest='batch_size', required=False, type=int, default=256)
    parser.add_argument("--worker-count", dest='worker_count', required=False, type=int, default=3)
    parser.add_argument("--steps-per-epoch", dest='steps_per_epoch', required=False, type=int, default=None)
    parser.add_argument("--device", dest='device', required=False,  default="/cpu:0", help="can be /cpu:0 or /gpu:0")
    return parser.parse_args()


def main():
    logger = setup_logging(log_file_name="predict_office_train.log")
    args = parse_args()

    model = TTensorFlowOfficeModel(logger, args.bigrams_path, args.model_folder, create_model=True,
                                   work_pool_path=args.train_pool,  row_count=args.row_count)
    model.train_tensorflow(args.dense_layer_size,
                               epoch_count=args.epoch_count,
                               batch_size=args.batch_size,
                               workers_count=args.worker_count,
                               steps_per_epoch=args.steps_per_epoch,
                               device_name=args.device
                               )


if __name__ == "__main__":
    main()
