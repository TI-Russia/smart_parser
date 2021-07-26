from common.logging_wrapper import setup_logging
from scripts.predict_office.office_index import TOfficeIndex
from scripts.predict_office.office_pool import TOfficePool, TPredictionCase
from common.russian_regions import TRussianRegions

from catboost import CatBoostClassifier, Pool
import numpy as np
import argparse
import operator


class TPredictionModel:
    def __init__(self, args):
        self.args = args
        self.logger = args.logger
        self.office_index = TOfficeIndex(args)
        self.office_index.read()
        self.learn_target_is_office = self.args.learn_target == "office"
        self.learn_target_is_region = self.args.learn_target.startswith("region")
        self.train_pool = None
        self.regions = TRussianRegions()

    def read_train(self):
        self.train_pool = TOfficePool(self, self.args.train_pool, row_count=self.args.row_count)
        assert len(self.train_pool.pool) > 0

    def read_test(self):
        self.test_pool = TOfficePool(self, self.args.test_pool, row_count=self.args.row_count)
        assert len(self.test_pool.pool) > 0

    def get_office_name_bigram_feature(self, case: TPredictionCase):
        bigrams_one_hot = np.zeros(len(self.office_index.office_name_bigrams))
        for b in TOfficeIndex.get_bigrams(case.text):
            bigram_id = self.office_index.office_name_bigrams.get(b)
            if bigram_id is not None:
                bigrams_one_hot[bigram_id] = 1
        return bigrams_one_hot

    def get_region_words_feature(self, case: TPredictionCase):
        one_hot = np.zeros(len(self.office_index.region_words))
        for b in TOfficeIndex.get_word_stems(case.text):
            word_id = self.office_index.region_words.get(b)
            if word_id is not None:
                one_hot[word_id] = 1

        return one_hot

    def get_web_domain_feature(self, case: TPredictionCase):
        web_domain_index = self.office_index.web_domains.get(case.web_domain, 0)
        web_domain_one_hot = np.zeros(len(self.office_index.web_domains))
        web_domain_one_hot[web_domain_index] = 1
        return web_domain_one_hot

    def get_learn_target_count(self):
        if self.learn_target_is_office:
            return len(self.office_index.offices)
        else:
            assert self.learn_target_is_region
            return 111

    def build_features(self, case: TPredictionCase):
        web_domain_index = self.office_index.web_domains.get(case.web_domain, 0)
        #text = " ".join(TOfficeIndex.get_word_stems(case.text[0:200]))
        #return np.array(list([web_domain_index, text]))
        region_id_from_text = self.regions.get_region_all_forms(case.text)
        if region_id_from_text is None:
            region_id_from_text = 0
        return np.array(list([web_domain_index, region_id_from_text]))

    def to_ml_input(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        features = list()
        for case in cases:
            features.append(self.build_features(case))
        labels = np.array(list(c.get_learn_target() for c in cases))

        #feature_names = ["web_domain_feat", "title_feat"]
        #text_features = ["title_feat"]

        feature_names = ["web_domain_feat", "region_id_from_text_feat"]
        cat_features = ["web_domain_feat", "region_id_from_text_feat"]
        catboost_test_pool = Pool(features, labels, feature_names=feature_names,
                                      cat_features=cat_features,
                                  #text_features=text_features
                                  )
        return catboost_test_pool

    def train_catboost(self, iter_count=100):
        self.logger.info("train_catboost iterations count={}".format(iter_count))
        catboost_pool = self.to_ml_input(self.train_pool.pool, "train")
        model = CatBoostClassifier(iterations=self.args.iter_count,
                                   depth=4,
                                   loss_function='MultiClass',
                                   verbose=True)
        model.fit(catboost_pool)
        model.save_model(self.args.model_path)

    def test(self):
        model = CatBoostClassifier()
        model.load_model(self.args.model_path)
        catboost_pool = self.to_ml_input(self.test_pool.pool, "test")
        res = model.score(catboost_pool)
        self.logger.info(res)

    def toloka(self):
        model = CatBoostClassifier()
        model.load_model(self.args.model_path)
        catboost_pool = self.to_ml_input(self.test_pool.pool, "test")
        test_y_pred = model.predict_proba(catboost_pool)
        test_y_max = list()
        for pred_proba_y in test_y_pred:
            (max_index, proba) = max(enumerate(pred_proba_y), key=operator.itemgetter(1))
            test_y_max.append((int(model.classes_[max_index]), proba))
        self.test_pool.build_toloka_pool(test_y_max, self.args.toloka_pool)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be bigrams, train, test, toloka")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--all-pool", dest='all_pool')
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-path", dest='model_path', required=False)
    parser.add_argument("--iter-count", dest='iter_count', required=False, type=int, default=10)
    parser.add_argument("--learn-target", dest='learn_target', required=False, default="office",
                        help="can be office, region, region_handmade",)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--toloka-pool", dest='toloka_pool', required=False)
    args = parser.parse_args()
    args.logger = setup_logging(log_file_name="predict_office.log")
    return args


def main():
    args = parse_args()
    if args.action == "bigrams":
        index = TOfficeIndex(args)
        index.build()
        index.write()
    else:
        model = TPredictionModel(args)
        if args.action == "split":
            args.all_pool is not None
            TOfficePool(model, args.all_pool).split(args.train_pool, args.test_pool)
        elif args.action == "train":
            model.read_train()
            model.train_catboost()
        elif args.action == "test":
            model.read_test()
            model.test()
        elif args.action == "toloka":
            model.read_test()
            assert args.toloka_pool is not None
            model.toloka()
        else:
            raise Exception("unknown action")


if __name__ == '__main__':
    main()

