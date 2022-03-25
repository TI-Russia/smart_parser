#draft, delete it in 2023

import os.path
import sys

from common.logging_wrapper import setup_logging
from predict_office.prediction_case import TPredictionCase
from predict_office.base_ml_model import TPredictionModelBase
from predict_office.office_index import TOfficePredictIndex
from predict_office.office_pool import TOfficePool
from predict_office.tensor_flow_model import TTensorFlowOfficeModel


from collections import defaultdict
from catboost import CatBoostClassifier, Pool
import numpy as np
import argparse


class TPredictionModelCatboost(TPredictionModelBase):

    def __init__(self, logger, office_index_path, model_path, create_model: bool, work_pool_path: str, row_count=None):
        super().__init__(logger, office_index_path, model_path, create_model=create_model,
                         work_pool_path=work_pool_path,
                         row_count=row_count)
        self.tf_model = TTensorFlowOfficeModel(logger, self.args.bigrams_path, self.args.model_folder,
                                               create_model=False, work_pool_path=work_pool_path, row_count=row_count)

    def get_catboost_model_path(self):
        return os.path.join(self.model_path, "catboost")

    def build_features_office_cb(self, case: TPredictionCase, tf_ml_office_id, tf_weight):
        web_domain_index = self.office_index.get_web_domain_index(case.web_domain)
        region_id_from_site_title = self.office_index.get_region_from_web_site_title(case.web_domain)
        region_id_from_text = self.office_index.regions.get_region_all_forms(case.text, 0)
        ml_office_id_by_site_url = self.office_index.get_parent_office_from_web_site(case.web_domain)
        features = np.array(list([
            web_domain_index,
            region_id_from_text,
            region_id_from_site_title,
            ml_office_id_by_site_url,
            tf_ml_office_id,
            tf_weight
            ]))

        self.logger.debug(features)
        return features

    def to_ml_input_office(self, cases, name):
        features = list()
        cnt = 0
        train_y_pred = self.tf_model.predict_cases(cases)
        for case, (tf_office_id, tf_weight) in zip(cases, train_y_pred):
            if cnt % 100 == 0:
                sys.stdout.write("{}/{}\r".format(cnt, len(cases)))
                sys.stdout.flush()
            cnt += 1
            tf_ml_office_id = self.office_index.office_id_2_ml_office_id(tf_office_id)
            features.append(self.build_features_office_cb(case, tf_ml_office_id , tf_weight))
        sys.stdout.write("\n")
        targets = list(c.get_learn_target() for c in cases)
        labels = np.array(targets)
        self.logger.info("number of distinct targets = {}".format(len(set(labels))))
        feature_names = ["web_domain_feat",
                         "region_id_from_text_feat",
                         "region_id_from_html_title",
                         "ml_office_id_by_site_url",
                         "tf_office_id",
                         "tf_weight"
                         ]
        self.logger.info("features={}".format(feature_names))
        cat_features = ["web_domain_feat", "region_id_from_text_feat", "region_id_from_html_title", "office_by_bigrams"]

        catboost_test_pool = Pool(features, labels, feature_names=feature_names,
                                      cat_features=cat_features,
                                  )
        return catboost_test_pool

    def to_ml_input(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        return self.to_ml_input_office(cases, name)

    def train_catboost(self):
        catboost_pool = self.to_ml_input(self.train_pool.pool, "train")
        self.logger.info("train_catboost iterations count={}".format(self.args.iter_count))
        model = CatBoostClassifier(iterations=self.args.iter_count,
                                   depth=4,
                                   logging_level="Debug",
                                   loss_function='MultiClass',
                                   #verbose=True
                                   )
        model.fit(catboost_pool)
        model.save_model(self.get_catboost_model_path())

    def test(self):
        model = CatBoostClassifier()
        model.load_model(self.args.model_path)
        catboost_pool = self.to_ml_input(self.test_pool.pool, "test")
        res = model.score(catboost_pool)
        self.logger.info(res)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-folder", dest='model_folder', required=False, default="model")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--iter-count", dest='iter_count', required=False, type=int, default=10)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    args = parser.parse_args()
    return args


def main():
    logger = setup_logging(log_file_name="predict_office_train_cb.log")
    args = parse_args()

    model = TPredictionModelCatboost(logger, args.bigrams_path, args.model_folder, crearow_count=.row_count,
                                   args.train_pool)
    model.train_catboost()


if __name__ == '__main__':
    main()

