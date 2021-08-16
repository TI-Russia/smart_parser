import sys

from disclosures_site.predict_office.prediction_case import TPredictionCase
from disclosures_site.predict_office.base_ml_model import TPredictionModelBase
from disclosures_site.predict_office.office_index import TOfficePredictIndex
import operator
import numpy as np
import tensorflow as tf

#https://github.com/tensorflow/tensorflow/issues/23748
# https://medium.com/dailymotion/how-to-design-deep-learning-models-with-sparse-inputs-in-tensorflow-keras-fd5e754abec1
class DenseLayerForSparse(tf.keras.layers.Layer):
    def __init__(self, vocabulary_size, units, **kwargs):
        super(DenseLayerForSparse, self).__init__()
        self.vocabulary_size = vocabulary_size
        self.units = units
        self.activation = tf.keras.activations.get(None)

    def build(self, input_shape):
        self.kernel = self.add_variable(
            "kernel", shape=[self.vocabulary_size, self.units]
        )
        self.bias = self.add_variable("bias", shape=[self.units])

    def call(self, inputs, **kwargs):
        outputs = tf.add(tf.sparse.sparse_dense_matmul(inputs, self.kernel), self.bias)
        return self.activation(outputs)

    def compute_output_shape(self, input_shape):
        input_shape = input_shape.get_shape().as_list()
        return input_shape[0], self.units

    def get_config(self):
        config = super().get_config().copy()
        config.update({
            'vocab_size': self.vocabulary_size,
            'units': self.units,
        })
        return config


class TTensorFlowOfficeModel(TPredictionModelBase):

    def get_web_domain_feature(self, case: TPredictionCase):
        web_domain_index = self.office_index.get_web_domain_index(case.web_domain)
        shape = [1, len(self.office_index.web_domains)]
        return tf.SparseTensor(indices=[(0, web_domain_index)], values=[1], dense_shape=shape)

    def convert_to_sparse_tensor(self, indices_to_be_set, shape):
        if len(indices_to_be_set) == 0:
            return tf.SparseTensor(indices=[[0, 0]],
                                   values=[0],
                                   dense_shape=shape)
        else:
            indices_to_be_set = list((0, i) for i in sorted(list(indices_to_be_set)))
            return tf.SparseTensor(indices=indices_to_be_set,
                           values=[1]*len(indices_to_be_set),
                           dense_shape=shape)

    def get_bigram_feature(self, case: TPredictionCase):
        site_title = self.office_index.web_sites.get_title_by_web_domain(case.web_domain)
        bigrams = set()
        for b in TOfficePredictIndex.get_bigrams(case.text + " " + site_title):
            bigram_id = self.office_index.get_bigram_id(b)
            if bigram_id is not None:
                bigrams.add(bigram_id)
        return sorted(list(bigrams))
        #shape = [self.office_index.get_bigrams_count(), 1]
        #return self.convert_to_sparse_tensor(bigrams, shape)

    def to_ml_input_features(self, cases, verbose=False):
        def get_bigram_feature_gen():
            for index, case in enumerate(cases):
                for bigram_id in self.get_bigram_feature(case):
                    yield index, bigram_id

        def get_web_domain_feature_gen():
            for index, case in enumerate(cases):
                web_domain_index = self.office_index.get_web_domain_index(case.web_domain)
                yield index, web_domain_index

        indices = list(get_bigram_feature_gen())
        values = [1.0] * len(indices)
        bigrams = tf.SparseTensor(indices=indices,
                               values=values,
                               dense_shape=(len(cases), self.office_index.get_bigrams_count())
                    )

        indices = list(get_web_domain_feature_gen())
        values = [1.0] * len(indices)
        web_domains = tf.SparseTensor(indices=indices,
                                  values=values,
                                  dense_shape=(len(cases), len(self.office_index.web_domains))
                                  )

# signature = tf.SparseTensorSpec (
        #     shape=(self.office_index.get_bigrams_count(), 1), dtype="int32"
        # )
        # dataset1 = tf.data.Dataset.from_generator(
        #     get_bigram_feature_gen,
        #     output_signature=signature
        # )
        # bigrams = tf.SparseTensor(
        #     dense_shape=(self.office_index.get_bigrams_count(), len(cases))
        # )
        # bigrams_l = list()
        # cnt = 0
        # for c in cases:
        #     bigrams_l.append(self.get_bigram_feature(c))
        #     if verbose:
        #         if cnt % 1000 == 0:
        #             sys.stdout.write("{}/{}\r".format(cnt, len(cases)))
        #             sys.stdout.flush()
        #         cnt += 1
        # sys.stdout.write("{}/{}\r".format(cnt, len(cases)))
        #web_domains_l = list(self.get_web_domain_feature(c) for c in cases)

        # return {
        #     "bigrams_feat": tf.sparse.concat(0, bigrams_l),
        #     "web_domain_feat": tf.sparse.concat(0, web_domains_l),
        # }

        return {
            "bigrams_feat": bigrams,
            "web_domain_feat": web_domains,
        }

    def to_ml_input(self, cases, name):
        self.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        labels = np.array(list(c.get_learn_target() for c in cases))
        return self.to_ml_input_features(cases, verbose=True), labels

    def init_model_before_train(self, dense_layer_size, input_data):
        inputs = list()
        # concate_len = 0
        # for i in input_data:
        #     inputs.append(tf.keras.Input(name=i, tensor=input_data[i]))
        #     concate_len += input_data[i].shape[1]
        # print(inputs[0])
        bigr_count = self.office_index.get_bigrams_count()
        dom_count = len(self.office_index.web_domains)
        inputs = [
           tf.keras.Input(shape=(bigr_count), name="bigrams_feat", sparse=True),
           tf.keras.Input(shape=(dom_count), name="web_domain_feat", sparse=True)
        ]
        concate_len = bigr_count + dom_count
        concatenated_layer = tf.keras.layers.concatenate(inputs)
        #dense_layer1 = tf.keras.layers.Dense(dense_layer_size)(concatenated_layer)
        #dense_layer1 = tf.keras.layers.Dense(dense_layer_size)(inputs)
        dense_layer1 = DenseLayerForSparse(concate_len, dense_layer_size)(concatenated_layer)
        dense_layer2 = tf.keras.layers.Dense(dense_layer_size)(dense_layer1)
        target_layer = tf.keras.layers.Dense(self.get_learn_target_count(), name="target",
                                             activation="softmax")(dense_layer2)
        model = tf.keras.Model(
            inputs=inputs,
            outputs=target_layer,
        )
        tf.keras.utils.plot_model(model, "predict_office.png", show_shapes=True)
        return model

    def train_tensorflow(self, dense_layer_size, epoch_count, batch_size=256, workers_count=3, steps_per_epoch=None,
                         device_name="/cpu:0"):
        assert self.model_path is not None
        self.logger.info("train_tensorflow layer_size={} batch_size={} workers_count={} epoch_count={} "
                         "steps_per_epoch={}".format(dense_layer_size, batch_size, workers_count, epoch_count,
                                                     steps_per_epoch))

        train_x, train_y = self.to_ml_input(self.train_pool.pool, "train")

        self.logger.info("init_model_before_train")
        model = self.init_model_before_train(dense_layer_size, train_x)
        self.logger.info(model.summary())

        self.logger.info("compile model...")
        model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])

        self.logger.info("training on device {}...".format(device_name))
        with tf.device(device_name):
            model.fit(train_x,
                      train_y,
                      epochs=epoch_count,
                      workers=workers_count,
                      batch_size=batch_size,
                      steps_per_epoch=steps_per_epoch,
                      #validation_split=0.2  not supported by sparse tensors
                      )
        self.logger.info("save to {}".format(self.model_path))
        model.save(self.model_path)
        #model = tf.keras.models.load_model(self.model_path)


    def load_model(self):
        self.logger.info("load tensorflow model from {}".format(self.model_path))
        model = tf.keras.models.load_model(self.model_path)
        return model

    def test(self, threshold=0.0):
        model = self.load_model()
        test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
        test_y_pred = model.predict(test_x)
        true_positive = 0
        false_positive = 0
        true_negative = 0
        false_negative = 0
        for true_ml_office_id, pred_proba_y in zip(test_y, test_y_pred):
            ml_office_id, weight = max(enumerate(pred_proba_y), key=operator.itemgetter(1))
            if weight > threshold:
                if true_ml_office_id == ml_office_id:
                    true_positive += 1
                else:
                    false_positive += 1
            else:
                if true_ml_office_id == ml_office_id:
                    false_negative += 1
                else:
                    true_negative += 1
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / (true_positive + false_negative)
        f1 = 2 * precision * recall /(precision + recall)
        self.logger.info("tp={}, fp={}, tn={}, fn={} "
                         .format(true_positive, false_positive, true_negative, false_negative))
        self.logger.info("threshold={}, precision={:.4f}, recall={:.4f}, f1={:.4f}, "
                         .format(threshold, precision, recall, f1))

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
        test_x = self.to_ml_input_features(self.test_pool.pool)
        test_y_pred = model.predict(test_x)
        self.test_pool.build_toloka_pool(self.office_index, test_y_pred, toloka_pool_path)
