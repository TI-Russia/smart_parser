import urllib.parse

import tensorflow as tf
import json
from common.logging_wrapper import setup_logging
import random
from sklearn.model_selection import train_test_split
import numpy as np
import re
import pymysql
from collections import defaultdict
import argparse
import operator


def get_word_stems(text):
    yield "^"
    for w in re.split("[\s,\.;:_\"* ()]", text.lower()):
        if len(w) > 0:
            if w.startswith("20") and len(w) == 4:
                continue
            #if len(w) <= 2:
            #    continue
            if len(w) <= 3:
                yield w
            else:
                yield w[0:3]
    yield "$"


def get_bigrams(text):
    words = list(get_word_stems(text))

    for w1, w2 in zip(words[:-1], words[1:]) :
        yield "_".join((w1, w2))


def get_trigrams(text):
    words = list(get_word_stems(text))

    for w1, w2, w3 in zip(words[:-2], words[1:-1], words[2:]) :
        yield "_".join((w1, w2, w3))


class TOfficeIndex:

    def __init__(self, args):
        self.args = args
        self.bigrams_index_by_str = None
        self.uniq_trigrams_to_office_id = None
        self.offices = None
        self.max_office_id = None
        self.web_domains = None

    def read(self):
        with open(self.args.bigrams_path) as inp:
            js = json.load(inp)
            self.bigrams_index_by_str = js['bigrams']
            self.uniq_trigrams_to_office_id = js['trigrams']
            self.max_office_id = js['max_office_id']
            self.offices = js['offices']
            self.web_domains = js['web_domains']
        self.args.logger.info("bigrams count = {}".format(len(self.bigrams_index_by_str)))

    def write(self):
        self.args.logger.info("write to {}".format(self.args.bigrams_path))
        with open(self.args.bigrams_path, "w") as outp:
            rec = {
                'bigrams': self.bigrams_index_by_str,
                'trigrams': self.uniq_trigrams_to_office_id,
                'max_office_id': self.max_office_id,
                'offices': self.offices,
                'web_domains': self.web_domains
            }
            json.dump(rec, outp, ensure_ascii=False, indent=4)

    def get_office_name(self, id):
        return self.offices[str(id)]['name']

    def get_office_region(self, id):
        return self.offices[str(id)]['region']

    def build(self):
        self.args.logger.info("build bigrams")
        db_connection = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
        in_cursor = db_connection.cursor()
        sql = "select id, name, region_id, calculated_params from declarations_office"
        self.args.logger.info(sql)
        in_cursor.execute(sql)
        bigrams_to_office_ids = defaultdict(set)
        trigram_to_office_ids = defaultdict(set)
        self.offices = dict()
        self.web_domains = dict()
        self.max_office_id = -1
        max_web_domain = 1
        for office_id, name, region_id, calculated_params in in_cursor:
            if region_id is None:
                region_id = 0
            self.offices[office_id] = {'name': name, 'region': int(region_id)}
            self.max_office_id = max(self.max_office_id, office_id)
            if name.lower().startswith("сведения о"):
                continue
            for b in get_bigrams(name):
                bigrams_to_office_ids[b].add(office_id)
            for b in get_trigrams(name):
                trigram_to_office_ids[b].add(office_id)
            for u in json.loads(calculated_params)['urls']:
                web_domain = urllib.parse.urlsplit(u).netloc
                if web_domain not in self.web_domains:
                    self.web_domains[web_domain] = max_web_domain
                    max_web_domain += 1
        db_connection.close()
        pairs = enumerate(sorted(bigrams_to_office_ids.keys()))
        self.bigrams_index_by_str = dict((k, i) for (i, k) in pairs)
        self.args.logger.info("bigrams count = {}".format(len(self.bigrams_index_by_str)))
        self.uniq_trigrams_to_office_id = dict()
        for key, value in trigram_to_office_ids.items():
            if len(value) == 1:
                self.uniq_trigrams_to_office_id[key] = list(value)[0]
        self.args.logger.info("uniq_trigrams_to_office_id count = {}".format(len(self.uniq_trigrams_to_office_id)))


class TPredictionCase:
    def __init__(self, ml_model=None, sha256=None, text=None, web_domain=None, true_office_id=None):
        self.ml_model = ml_model
        self.sha256 = sha256
        self.text = text
        self.web_domain = web_domain
        self.true_office_id = true_office_id
        self.true_region_id = ml_model.office_index.get_office_region(true_office_id)

    def from_json(self, js):
        self.__dict__ = json.loads(js)

    def get_features_count(self):
        cnt = len(self.ml_model.office_index.bigrams_index_by_str.keys())
        return cnt + 1

    def to_json(self, js):
        return json.dumps(self.__dict__, ensure_ascii=False)

    def build_features(self):
        features = np.zeros(self.get_features_count(), dtype='int')
        for b in get_bigrams(self.text):
            bigram_id = self.ml_model.office_index.bigrams_index_by_str.get(b)
            if bigram_id is not None:
                features[bigram_id] = 1
        features[-1] = self.ml_model.office_index.web_domains.get(self.web_domain, 0)
        return features

    def get_learn_target(self):
        if self.ml_model.learn_target_is_office:
            return self.true_office_id
        else:
            return self.true_region_id

    #  пока не используется, дает слишком низкую точность
    def check_uniq_trigram(self):
        hypots = defaultdict(set)
        for t in get_trigrams(self.text):
            office_id = self.ml_model.office_index.uniq_trigrams_to_office_id.get(t)
            if office_id is not None:
                hypots[office_id].add(t)
        self.ml_model.logger.debug("{} -> {}".format(self.text, hypots))
        if len(hypots) == 0:
            return None
        if len(hypots) == 1:
            office_id = list(hypots.keys())[0]
            if len(hypots[office_id]) > 1:
                return office_id
            else:
                return None

        sorted_hypots = sorted(((len(v), k) for (k, v) in hypots.items()), reverse=True)
        if sorted_hypots[1][0] * 3 <= sorted_hypots[0][0]:
            return sorted_hypots[0][1]
        return None

    #select d.sha256, f.web_domain, d.office_id from declarations_declarator_file_reference f join declarations_source_document d on d.id = f.source_document_id  into  outfile "/tmp/docs.txt";
#cut -f 1  /tmp/docs.txt >/tmp/docs.txt.id
#python3 ~/smart_parser/tools/smart_parser_http/smart_parser_client.py --action title --sha256-list /tmp/docs.txt.id > /tmp/docs_titles.txt
#paste /tmp/docs.txt /tmp/docs_titles.txt >/tmp/office_declarator_pool.txt

class TOfficePool:
    def __init__(self, ml_model, file_name: str, row_count=None):
        self.pool = list()
        self.ml_model = ml_model
        self.logger = ml_model.logger
        self.read_cases(file_name, row_count)
        self.delete_deterministic_web_domains()
        self.logger.info("read from {} {} cases".format(file_name, len(self.pool)))

    def check_uniq_trigram_heuristic(self):
        tp = 0
        fp = 0
        case: TPredictionCase
        for case in self.pool:
            heuristic_office_id = case.check_uniq_trigram()
            if heuristic_office_id is not None:
                if case.true_office_id == heuristic_office_id:
                    tp += 1
                else:
                    heuristic_office_id = case.check_uniq_trigram()
                    self.logger.debug("error uniq trigram doc {} true_office={} ( id = {} ) "
                                      "predicted={} (id = {} )".format(
                        case.sha256,
                        self.ml_model.office_index.get_office_name(case.true_office_id), case.true_office_id,
                        self.ml_model.office_index.get_office_name(heuristic_office_id), heuristic_office_id))
                    fp += 1
        self.logger.info("check_uniq_trigram_heuristic tp={}, fp={}, prec = {}".format(tp, fp, tp/(tp+fp+0.0000000001)))

    def read_cases(self, file_name: str, row_count=None):
        cnt = 0
        with open(file_name, "r") as inp:
            for line in inp:
                try:
                    sha256, web_domain, office_id, title = line.strip().split("\t")

                    case = TPredictionCase(self.ml_model, sha256, title, web_domain, int(office_id))
                    self.pool.append(case)
                    cnt += 1
                    if row_count is not None and cnt >= row_count:
                        break
                except ValueError as err:
                    self.logger.debug("cannot parse line {}, skip it".format(line.strip()))
                    pass
        self.logger.info("read {} cases from {}".format(cnt, file_name))

    @staticmethod
    def write_pool(cases, output_path):
        c: TPredictionCase
        with open(output_path, "w") as outp:
            for c in cases:
                outp.write("{}\n".format("\t".join([c.sha256, c.web_domain,  str(c.true_office_id), c.text])))

    def split(self, train_pool_path, test_pool_path):
        random.shuffle(self.pool)
        train, test = train_test_split(self.pool, test_size=0.2)
        self.write_pool(train, train_pool_path)
        self.write_pool(test, test_pool_path)
        self.ml_model.logger.info("train size = {}, test size = {}".format(len(train), len(test)))

    def delete_deterministic_web_domains(self):
        office_by_web_domain = defaultdict(set)
        for c in self.pool:
            office_by_web_domain[c.web_domain].add(c.true_office_id)
        new_pool = list()
        for c in self.pool:
            if c.text == "null" or len(c.text) == 0:
                continue
            if len(office_by_web_domain[c.web_domain]) <= 1:
                continue
            new_pool.append(c)
        self.pool = new_pool
        self.logger.info("leave only {} after deterministic web domain filtering".format(len(self.pool)))


class TPredictionModel:
    def __init__(self, args):
        self.args = args
        self.logger = args.logger
        self.office_index = TOfficeIndex(args)
        self.office_index.read()
        self.learn_target_is_office = self.args.learn_target == "office"
        self.learn_target_is_region = self.args.learn_target == "region"
        self.train_pool = None
        self.features_count = None

    def read_train(self):
        self.train_pool = TOfficePool(self, self.args.train_pool, row_count=self.args.row_count)
        assert len(self.train_pool.pool) > 0
        self.features_count = self.train_pool.pool[0].get_features_count()

    def read_test(self):
        self.test_pool = TOfficePool(self, self.args.test_pool, row_count=self.args.row_count)
        assert len(self.test_pool.pool) > 0
        self.features_count = self.test_pool.pool[0].get_features_count()

    def to_ml_input(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        features = list()
        labels = list()
        c: TPredictionCase
        for cnt, c in enumerate(cases):
            features.append(c.build_features())
            labels.append(c.get_learn_target())
            if cnt % 10000 == 0:
                print(".")
        return np.array(features), np.array(labels)

    def create_test_and_train(self, cases):
        random.shuffle(cases)
        return train_test_split(cases, test_size=0.2)

            #cat office_declarator_pool.txt | shuf >a
        #head -n 200000 office_declarator_pool.txt >train_pool.txt
        #tail -n 67276 office_declarator_pool.txt >test_pool.txt


    def build_toloka_pool(self, cases, test_y_pred, output_path):
        assert len(cases) == len(test_y_pred)

        with open(output_path, "w") as outp:
            case: TPredictionCase
            for case, pred_proba_y in zip(cases, test_y_pred):
                pred_target, pred_proba  = max( enumerate(pred_proba_y), key=operator.itemgetter(1))
                rec = {
                    "status": ("positive" if case.get_learn_target() == pred_target else "negative"),
                    "true_office_id": case.true_office_id,
                    "true_office_name": self.office_index.get_office_name(case.true_office_id),
                    "true_region_id": case.true_region_id,
                    "doc_title": case.text,
                    "sha256": case.sha256,
                    "web_domain": case.web_domain,
                    "pred_proba": float(pred_proba)
                }
                if self.learn_target_is_office:
                    rec['pred_office_name'] = self.office_index.get_office_name(pred_target)
                    rec['pred_office_id'] = pred_target
                else:
                    rec['pred_region_id'] = pred_target
                outp.write("{}\n".format(json.dumps(rec, ensure_ascii=False)))

    def init_model(self):
        return tf.keras.Sequential([
            tf.keras.layers.Dense(self.args.layer_size, activation='relu', input_shape=(self.features_count,)),
            tf.keras.layers.Dense(self.args.layer_size),
            # tf.keras.layers.Dropout(0.5),
            # tf.keras.layers.Dense(1, activation="sigmoid", bias_initializer=output_bias)
            tf.keras.layers.Dense(self.office_index.max_office_id + 1, activation="softmax")
        ])

    def train_tensorflow(self):
        assert self.args.model_folder is not None
        #batch_size = 64 prod?
        batch_size = 256
        self.logger.info("train_tensorflow layer_size={}".format(self.args.layer_size))
        train_x, train_y = self.to_ml_input(self.train_pool.pool, "train")
        assert self.features_count == train_x.shape[-1]

        model = self.init_model()

        model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])

        model.fit(train_x, train_y,
                  epochs=self.args.epoch_count,
                  workers=3,
                  batch_size=batch_size,
                  validation_split=0.2)
        model.save(self.args.model_folder)

    def test(self):
        model = tf.keras.models.load_model(self.args.model_folder)
        test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
        res = model.evaluate(test_x, test_y)
        self.logger.info(res)

    def toloka(self):
        model = tf.keras.models.load_model(self.args.model_folder)
        test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
        test_y_pred = model.predict(test_x)
        self.build_toloka_pool(self.test_pool.pool, test_y_pred, self.args.toloka_pool)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be bigrams, train, test, toloka")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--all-pool", dest='all_pool')
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
    parser.add_argument("--learn-target", dest='learn_target', required=False, default="office", help="can be office or region")
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--layer-size", dest='layer_size', required=False, type=int, default=256)
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

