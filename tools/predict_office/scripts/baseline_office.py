from common.logging_wrapper import setup_logging
from predict_office.prediction_case import TPredictionCase
from predict_office.base_ml_model import TPredictionModelBase

import argparse


def test_baseline(model: TPredictionModelBase):
    c: TPredictionCase
    true_positive = 0
    false_positive = 0

    for c in model.test_pool.pool:
        site_info = model.office_index.web_sites.get_first_site_by_web_domain(c.web_domain)
        if site_info is None:
            raise Exception ("cannot find site info for {}".format(c.web_domain))
        if c.true_office_id == site_info.calculated_office_id:
            true_positive += 1
        else:
            false_positive += 1
    model.logger.info("tp={}, fp={}".format(true_positive, false_positive))
    precision =  true_positive / (true_positive + false_positive)
    recall = true_positive / (len(model.test_pool.pool))
    f1 = 2 * precision * recall / (precision + recall)
    model.logger.info("precision = {:.4f}, recall = {:.4f}, f1={:.4f},  pool size = {}".format(
        precision, recall, f1, len(model.test_pool.pool)))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--test-pool", dest='test_pool')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging(log_file_name="predict_office_baseline.log")
    model = TPredictionModelBase(logger, args.bigrams_path, args.model_folder,
                             test_pool=args.test_pool)
    test_baseline(model)


if __name__ == "__main__":
    main()
