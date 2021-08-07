from common.logging_wrapper import setup_logging
from scripts.predict_office.office_pool import  TPredictionCase
from scripts.predict_office.predict_office_model import TPredictionModelBase

import argparse
from sklearn.metrics import accuracy_score


class TPredictionModel(TPredictionModelBase):

    def test(self):
        y_true = list()
        y_pred = list()
        y_pred_proba = list()
        c: TPredictionCase
        for c in self.test_pool.pool:
            site_info = self.office_index.web_sites.get_site_by_web_domain(c.web_domain)
            if site_info is None:
                raise Exception ("cannot find site info for {}".format(c.web_domain))
            pred_office_id = site_info.calculated_office_id
            y_pred_proba.append((pred_office_id, 1))
            y_pred.append(pred_office_id)
            y_true.append(c.true_office_id)
        self.logger.info("accuracy = {} pool size = {}".format(accuracy_score(y_true, y_pred), len(y_true)))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can  test")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--learn-target", dest='learn_target', required=False, default="office",
                        help="can be office, region, region_handmade",)

    args = parser.parse_args()
    args.logger = setup_logging(log_file_name="predict_office.log")
    return args


def main():
    args = parse_args()
    model = TPredictionModel(args)
    if args.action == "test":
        model.read_test()
        model.test()
    else:
        raise Exception("unknown action")


if __name__ == '__main__':
    main()

