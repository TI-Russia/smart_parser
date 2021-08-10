from disclosures_site.predict_office.prediction_case import TPredictionCase
from disclosures_site.predict_office.base_ml_model import TPredictionModelBase

import operator
import numpy as np
import tensorflow as tf


class TTensorFlowOfficeModel(TPredictionModelBase):

    def get_web_domain_feature(self, case: TPredictionCase):
        web_domain_index = self.office_index.web_domains.get(case.web_domain, 0)
        web_domain_one_hot = np.zeros(len(self.office_index.web_domains))
        web_domain_one_hot[web_domain_index] = 1
        return web_domain_one_hot

    def to_ml_input_features(self, cases):
        bigrams = list(self.office_index.get_bigram_feature_plus(c.text, c.web_domain) for c in cases)
        web_domains = list(self.get_web_domain_feature(c) for c in cases)
        return  {
            "office_name_feat": np.array(bigrams),
            "web_domain_feat": np.array(web_domains),
        }

    def to_ml_input(self, cases, name):
        self.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        labels = np.array(list(c.get_learn_target() for c in cases))
        return self.to_ml_input_features(cases), labels

    def init_model_before_train(self, dense_layer_size):
        office_name_input = tf.keras.Input(shape=(self.office_index.get_bigrams_count(),), name="office_name_feat")

        web_domain_count = len(self.office_index.web_domains)
        web_domain_input = tf.keras.Input(shape=(web_domain_count,), name="web_domain_feat")

        inputs = [
            office_name_input,
            web_domain_input,
        ]
        concatenated_layer = tf.keras.layers.concatenate(inputs)
        dense_layer1 = tf.keras.layers.Dense(dense_layer_size)(concatenated_layer)
        dense_layer2 = tf.keras.layers.Dense(dense_layer_size)(dense_layer1)
        target_layer = tf.keras.layers.Dense(self.get_learn_target_count(), name="target",
                                             activation="softmax")(dense_layer2)
        model = tf.keras.Model(
            inputs=inputs,
            outputs=target_layer,
        )
        tf.keras.utils.plot_model(model, "predict_office.png", show_shapes=True)
        return model

    def train_tensorflow(self, dense_layer_size, epoch_count):
        assert self.model_path is not None
        #batch_size = 64
        batch_size = 256
        self.logger.info("train_tensorflow layer_size={}".format(dense_layer_size))
        train_x, train_y = self.to_ml_input(self.train_pool.pool, "train")

        model = self.init_model_before_train(dense_layer_size)
        print(model.summary())
        model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])

        model.fit(train_x,
                  train_y,
                  epochs=epoch_count,
                  workers=3,
                  batch_size=batch_size,
                  validation_split=0.2)
        model.save(self.model_path)

    def load_model(self):
        self.logger.info("load tensorflow model from {}".format(self.model_path))
        model = tf.keras.models.load_model(self.model_path)
        return model

    def test(self):
        model = self.load_model()
        test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
        res = model.evaluate(test_x, test_y)
        self.logger.info(res)
        debug = model.predict(test_x)

    def predict(self, model, cases):
        if len(cases) == 0:
            return list()

        test_x = self.to_ml_input_features(cases)
        test_y_pred = model.predict(test_x)
        test_y_max = list()
        for pred_proba_y in test_y_pred:
            learn_target, weight = max(enumerate(pred_proba_y), key=operator.itemgetter(1))
            office_id = self.office_index.get_office_id_by_ml_office_id(learn_target)
            test_y_max.append((office_id, weight))
        return test_y_max

    def predict_by_portions(self, cases, portion_size=500):
        model = self.load_model()
        result = list()
        for start in range(0, len(cases), portion_size):
            portion = cases[start:start+portion_size]
            portion_result = self.predict(model, portion)
            result.extend(portion_result)

        assert (len(result) == len(cases))
        return result

    def toloka(self, toloka_pool_path: str):
        model = self.load_model()
        test_y_max = self.predict(model, self.test_pool.pool)
        self.test_pool.build_toloka_pool(test_y_max, toloka_pool_path)
