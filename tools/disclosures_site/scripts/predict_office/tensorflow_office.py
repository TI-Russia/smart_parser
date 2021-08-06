from common.logging_wrapper import setup_logging
from scripts.predict_office.office_index import TOfficeIndex
from scripts.predict_office.office_pool import TOfficePool, TPredictionCase
from scripts.predict_office.predict_office_model import TPredictionModelBase

import tensorflow as tf
import numpy as np
import argparse
import operator


class TPredictionModel(TPredictionModelBase):

    def get_office_name_bigram_feature(self, case: TPredictionCase):
        bigrams_one_hot = np.zeros(self.office_index.get_bigrams_count())
        for b in TOfficeIndex.get_bigrams(case.text):
            bigram_id = self.office_index.get_bigram_id(b)
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

    def to_ml_input_functional(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        bigrams = np.array(list(self.get_office_name_bigram_feature(c) for c in cases))

        web_domains = np.array(list(self.get_web_domain_feature(c) for c in cases))
        features = {
            "office_name_feat": bigrams,
            "web_domain_feat": web_domains,
            "region_name_feat": np.array(list(self.get_region_words_feature(c) for c in cases))
        }

        labels = np.array(list(c.get_learn_target() for c in cases))
        return features, labels

    def to_ml_input(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        bigrams = np.array(list(self.get_office_name_bigram_feature(c) for c in cases))
        labels = np.array(list(c.get_learn_target() for c in cases))
        return bigrams, labels

    def init_model(self):
        input_shape = (self.office_index.get_bigrams_count(),)
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(self.args.dense_layer_size, activation='relu', input_shape=input_shape),
            tf.keras.layers.Dense(self.args.dense_layer_size),
            tf.keras.layers.Dense(self.get_learn_target_count(), activation="softmax")
        ])
        return model

    def init_model_functional(self):
        office_name_input = tf.keras.Input(shape=(self.office_index.get_bigrams_count(),), name="office_name_feat")

        web_domain_count = len(self.office_index.web_domains)
        web_domain_input = tf.keras.Input(shape=(web_domain_count,), name="web_domain_feat")

        #region_word_count = len(self.office_index.region_words)
        #region_words_input = tf.keras.Input(shape=(region_word_count,), name="region_name_feat")

        inputs = [
            office_name_input,
            #web_domain_input,
            #region_words_input
        ]
        #inputs = [web_domain_input, region_words_input]
        #concatenated_layer = tf.keras.layers.concatenate(inputs)
        #input_layer = tf.keras.layers.Dense(self.args.dense_layer_size, activation='relu', input_shape=(self.train_x.shape[-1],)),
        dense_layer1 = tf.keras.layers.Dense(self.args.dense_layer_size)(office_name_input)
        dense_layer2 = tf.keras.layers.Dense(self.args.dense_layer_size)(dense_layer1)
        target_layer = tf.keras.layers.Dense(self.get_learn_target_count(), name="target")(dense_layer2)
        model = tf.keras.Model(
            inputs=inputs,
            outputs=target_layer,
        )
        tf.keras.utils.plot_model(model, "predict_office.png", show_shapes=True)
        return model

    def train_tensorflow(self):
        assert self.args.model_folder is not None
        #batch_size = 64
        batch_size = 256
        self.logger.info("train_tensorflow layer_size={}".format(self.args.dense_layer_size))
        train_x, train_y = self.to_ml_input(self.train_pool.pool, "train")

        model = self.init_model()
        print(model.summary())
        model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])

        model.fit(train_x,
                  train_y,
                  epochs=self.args.epoch_count,
                  workers=3,
                  batch_size=batch_size,
                  validation_split=0.2)
        model.save(self.args.model_folder)


    def test(self):
        if self.args.learn_target == "region_handmade":
            self.build_handmade_regions(self.test_pool)
        else:
            model = tf.keras.models.load_model(self.args.model_folder)
            test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
            res = model.evaluate(test_x, test_y)
            self.logger.info(res)
            debug = model.predict(test_x)
            pass

    def toloka(self):
        if self.args.learn_target == "region_handmade":
            test_y_pred = self.build_handmade_regions(self.test_pool)
            self.test_pool.build_toloka_pool(test_y_pred, self.args.toloka_pool)
        else:
            model = tf.keras.models.load_model(self.args.model_folder)
            test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
            test_y_pred = model.predict(test_x)
            test_y_max = list()
            for pred_proba_y in test_y_pred:
                test_y_max.append( max(enumerate(pred_proba_y), key=operator.itemgetter(1)) )
            self.test_pool.build_toloka_pool(test_y_max, self.args.toloka_pool)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be bigrams, train, test, toloka, split")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--all-pool", dest='all_pool')
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
    parser.add_argument("--learn-target", dest='learn_target', required=False, default="office",
                        help="can be office, region, region_handmade",)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--dense-layer-size", dest='dense_layer_size', required=False, type=int, default=256)
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
            model.train_tensorflow()
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

