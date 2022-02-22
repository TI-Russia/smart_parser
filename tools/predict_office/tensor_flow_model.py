from predict_office.prediction_case import TPredictionCase
from predict_office.base_ml_model import TPredictionModelBase
from predict_office.office_index import TOfficePredictIndex
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

    def get_name_bigram_feature(self, case: TPredictionCase):
        site_title = self.office_index.web_sites.get_title_by_web_domain(case.web_domain)
        bigrams = set()
        for b in TOfficePredictIndex.get_bigrams(case.text + " " + site_title):
            bigram_id = self.office_index.get_bigram_id(b)
            if bigram_id is not None:
                bigrams.add(bigram_id)
        return sorted(list(bigrams))

    def get_name_unigram_feature(self, case: TPredictionCase):
        site_title = self.office_index.web_sites.get_title_by_web_domain(case.web_domain)
        unigrams = set()
        for b in TOfficePredictIndex.get_word_stems(case.text + " " + site_title):
            ngram_id = self.office_index.get_unigram_id(b)
            if ngram_id is not None:
                unigrams.add(ngram_id)
        return sorted(list(unigrams))

    def get_region_feature(self, case: TPredictionCase):
        site_title = self.office_index.web_sites.get_title_by_web_domain(case.web_domain)
        txt = case.text + " " + site_title
        return self.office_index.regions.get_region_all_forms(txt, unknown_region=0)

    def to_ml_input_features(self, cases):
        def get_name_bigram_feature_gen():
            for index, case in enumerate(cases):
                for ngram_id in self.get_name_bigram_feature(case):
                    yield index, ngram_id

        def get_name_unigram_feature_gen():
            for index, case in enumerate(cases):
                for ngram_id in self.get_name_unigram_feature(case):
                    yield index, ngram_id

        def get_web_domain_feature_gen():
            for index, case in enumerate(cases):
                sorted_ids = sorted(set(self.office_index.get_web_domain_index(w)
                             for w in TOfficePredictIndex.split_web_domain(case.web_domain)))
                for id in sorted_ids:
                    yield index, id

        def get_region_feature_gen():
            for index, case in enumerate(cases):
                region_id = self.get_region_feature(case)
                yield index, region_id

        indices = list(get_name_bigram_feature_gen())
        values = [1.0] * len(indices)
        bigrams = tf.SparseTensor(indices=indices,
                               values=values,
                               dense_shape=(len(cases), self.office_index.get_bigrams_count())
                    )

        indices = list(get_name_unigram_feature_gen())
        values = [1.0] * len(indices)
        unigrams = tf.SparseTensor(indices=indices,
                               values=values,
                               dense_shape=(len(cases), self.office_index.get_unigrams_count())
                    )

        indices = list(get_web_domain_feature_gen())
        values = [1.0] * len(indices)
        web_domains = tf.SparseTensor(indices=indices,
                                  values=values,
                                  dense_shape=(len(cases), self.office_index.get_web_domains_count())
                                  )

        indices = list(get_region_feature_gen())
        values = [1.0] * len(indices)
        region_words = tf.SparseTensor(indices=indices,
                               values=values,
                               dense_shape=(len(cases), self.office_index.get_max_region_id() + 1)
                    )

        return {
            "bigrams_feat": bigrams,
            "web_domain_feat": web_domains,
            "unigrams_feat": unigrams,
            "region_words": region_words
        }

    def to_ml_input(self, cases, name):
        self.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        labels = np.array(list(c.get_learn_target() for c in cases))
        return self.to_ml_input_features(cases), labels

    def init_model_before_train(self, dense_layer_size, input_data):
        inputs = list()
        dense_after_input  = list()
        len_sum = 0
        for i in input_data:
            len = input_data[i].shape[1]
            input_layer = tf.keras.Input(name=i, shape=(len,), sparse=True)
            inputs.append(input_layer)
            dense_layer = DenseLayerForSparse(len, dense_layer_size)(input_layer)
            dense_after_input.append(dense_layer)
            len_sum += len

        concatenated_layer = tf.keras.layers.concatenate(dense_after_input)

        #ValueError: The last dimension of the inputs to `Dense` should be defined. Found `None`
        dense_layer1 = tf.keras.layers.Dense(dense_layer_size)(concatenated_layer)

        #dense_layer1 = DenseLayerForSparse(len_sum, dense_layer_size)(concatenated_layer)


        #dense_layer2 = tf.keras.layers.Dense(dense_layer_size)(dense_layer1)
        target_layer = tf.keras.layers.Dense(self.get_learn_target_count(), name="target",
                                             activation="softmax")(dense_layer1)
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
                      )
        self.logger.info("save to {}".format(self.model_path))
        model.save(self.model_path)

    def load_model(self):
        self.logger.info("load tensorflow model from {}".format(self.model_path))
        model = tf.keras.models.load_model(self.model_path)
        return model

    def calc_on_threshold(self, cases, test_y, test_y_pred, threshold, verbose=True):
        true_positive = 0
        false_positive = 0
        true_negative = 0
        false_negative = 0
        for case, true_ml_office_id, pred_proba_y in zip(cases, test_y, test_y_pred):
            if verbose:
                for ml_office_id, weight in enumerate(pred_proba_y):
                    if weight > threshold or ml_office_id == true_ml_office_id:
                        self.logger.debug("pred_office_id = {} weight = {} sha256 = {}".format(
                             self.office_index.get_office_id_by_ml_office_id(ml_office_id), weight, case.sha256 ))
            ml_office_id, weight = max(enumerate(pred_proba_y), key=operator.itemgetter(1))
            if weight > threshold:
                if true_ml_office_id == ml_office_id:
                    true_positive += 1
                    status = "true_positive"
                else:
                    false_positive += 1
                    status = "false_positive"
            else:
                if true_ml_office_id == ml_office_id:
                    false_negative += 1
                    status = "false_negative"
                else:
                    true_negative += 1
                    status = "true_negative"
            true_office_id = self.office_index.get_office_id_by_ml_office_id(true_ml_office_id)
            pred_office_id = self.office_index.get_office_id_by_ml_office_id(ml_office_id)
            if self.office_index.is_office_child_or_grandchild(true_office_id, pred_office_id):
                status += "(pred_parent_office)"
            self.logger.debug("{} true_office_id = {} pred_office_id = {} weight = {} sha256 = {}".format(
                status, true_office_id,
                pred_office_id, weight, case.sha256))
        precision = true_positive / (true_positive + false_positive + 0.000000000000000000001)
        recall = true_positive / (true_positive + false_negative + 0.000000000000000000001)
        f1 = 2 * precision * recall /(precision + recall + 0.000000000000000000001)
        self.logger.info("threshold={}, prec={:.4f}, recall={:.4f}, f1={:.4f}, tp={}, fp={}, tn={}, fn={} "
                         .format(threshold, precision, recall, f1,
                                 true_positive, false_positive, true_negative, false_negative))

    def test_model(self, thresholds=[0.6]):
        model = self.load_model()
        test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
        test_y_pred = model.predict(test_x)
        for threshold in thresholds:
            self.calc_on_threshold(self.test_pool.pool, test_y, test_y_pred, threshold)

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

    def toloka(self, toloka_pool_path: str, format=1):
        model = self.load_model()
        assert len(self.test_pool.pool) > 0
        test_x = self.to_ml_input_features(self.test_pool.pool)
        test_y_pred = model.predict(test_x)
        self.test_pool.build_toloka_pool(test_y_pred, toloka_pool_path, format=format)
