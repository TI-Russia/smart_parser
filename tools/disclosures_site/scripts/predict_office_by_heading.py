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

    def read(self):
        with open(self.args.bigrams_path) as inp:
            js = json.load(inp)
            self.bigrams_index_by_str = js['bigrams']
            self.uniq_trigrams_to_office_id = js['trigrams']
            self.max_office_id = js['max_office_id']
            self.offices = js['offices']
        self.args.logger.info("bigrams count = {}".format(len(self.bigrams_index_by_str)))

    def write(self):
        self.args.logger.info("write to {}".format(self.args.bigrams_path))
        with open(self.args.bigrams_path, "w") as outp:
            rec = {
                'bigrams': self.bigrams_index_by_str,
                'trigrams': self.uniq_trigrams_to_office_id,
                'max_office_id': self.max_office_id,
                'offices': self.offices
            }
            json.dump(rec, outp, ensure_ascii=False, indent=4)

    def get_office_name(self, id):
        return self.offices[str(id)]

    def build(self):
        self.args.logger.info("build bigrams")
        db_connection = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
        in_cursor = db_connection.cursor()
        sql = "select id, name, calculated_params from declarations_office"
        self.args.logger.info(sql)
        in_cursor.execute(sql)
        bigrams_to_office_ids = defaultdict(set)
        trigram_to_office_ids = defaultdict(set)
        self.offices = dict()
        self.max_office_id = -1
        for office_id, name, calculated_params in in_cursor:
            self.offices[office_id] = name
            self.max_office_id = max(self.max_office_id, office_id)
            if name.lower().startswith("сведения о"):
                continue
            for b in get_bigrams(name):
                bigrams_to_office_ids[b].add(office_id)
            for b in get_trigrams(name):
                trigram_to_office_ids[b].add(office_id)
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
    def __init__(self, sha256=None, text=None, web_domain=None, true_office_id=None):
        self.sha256 = sha256
        self.text = text
        self.web_domain = web_domain
        self.true_office_id = true_office_id

    def from_json(self, js):
        self.__dict__ = json.loads(js)

    def to_json(self, js):
        return json.dumps(self.__dict__, ensure_ascii=False)

    def build_features(self, office_index: TOfficeIndex):
        features_count = len(office_index.bigrams_index_by_str.keys())
        features = np.zeros(features_count, dtype='bool')
        for b in get_bigrams(self.text):
            bigram_id = office_index.bigrams_index_by_str.get(b)
            if bigram_id is not None:
                features[bigram_id] = True
        return features

    #  пока не используется, дает слишком низкую точность
    def check_uniq_trigram(self, office_index: TOfficeIndex, logger=None):
        hypots = defaultdict(set)
        for t in get_trigrams(self.text):
            office_id = office_index.uniq_trigrams_to_office_id.get(t)
            if office_id is not None:
                hypots[office_id].add(t)
        if logger is not None:
            logger.debug("{} -> {}".format(self.text, hypots))
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

class TLearnPoll:
    def __init__(self, logger, file_name: str, office_index=None, row_count=None):
        self.pool = list()
        self.logger = logger
        self.office_index = office_index
        self.read_cases(file_name, row_count)
        self.delete_deterministic_web_domains()

    def check_uniq_trigram_heuristic(self):
        tp = 0
        fp = 0
        case: TPredictionCase
        for case in self.pool:
            heuristic_office_id = case.check_uniq_trigram(self.office_index)
            if heuristic_office_id is not None:
                if case.true_office_id == heuristic_office_id:
                    tp += 1
                else:
                    heuristic_office_id = case.check_uniq_trigram(self.office_index, logger=self.logger)
                    self.logger.debug("error uniq trigram doc {} true_office={} ( id = {} ) "
                                      "predicted={} (id = {} )".format(
                        case.sha256,
                        self.office_index.get_office_name(case.true_office_id), case.true_office_id,
                        self.office_index.get_office_name(heuristic_office_id), heuristic_office_id))
                    fp += 1
        self.logger.info("check_uniq_trigram_heuristic tp={}, fp={}, prec = {}".format(tp, fp, tp/(tp+fp+0.0000000001)))

    def read_cases(self, file_name: str, row_count=None):
        cnt = 0
        with open(file_name, "r") as inp:
            for line in inp:
                try:
                    sha256, web_domain, office_id, title = line.strip().split("\t")

                    case = TPredictionCase(sha256, title, web_domain, int(office_id))
                    self.pool.append(case)
                    cnt += 1
                    if row_count is not None and cnt >= row_count:
                        break
                except ValueError as err:
                    self.logger.debug("cannot parse line {}, skip it".format(line.strip()))
                    pass
        self.logger.info("read {} cases from {}".format(cnt, file_name))

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

        self.train_x = None
        self.train_y = None
        self.test_x = None
        self.test_y = None
        self.learn_pool = TLearnPoll(self.logger, args.learn_pool, office_index=self.office_index, row_count=args.row_count)
        self.args.logger.info("read from {} {} cases".format(args.learn_pool, len(self.learn_pool.pool)))
        self.create_test_and_train(self.learn_pool.pool)

    def to_ml_input(self, cases, name):
        self.args.logger.info("build {} pool of {} cases".format(name, len(cases)))
        features = list()
        labels = list()
        c: TPredictionCase
        for cnt, c in enumerate(cases):
            features.append(c.build_features(self.office_index))
            labels.append(c.true_office_id)
            if cnt % 10000 == 0:
                print(".")
        return np.array(features), np.array(labels)

    def create_test_and_train(self, cases):
        random.shuffle(cases)
        train, test = train_test_split(cases, test_size=0.2)
        self.train_x, self.train_y = self.to_ml_input(train, "train")
        self.test_x, self.test_y = self.to_ml_input(test, "test")

    def train_tensorflow(self, epochs_count=10):
        batch_size = 512
        self.logger.info("train_tensorflow layer_size={}".format(self.args.layer_size))

        model = tf.keras.Sequential([
             tf.keras.layers.Dense(self.args.layer_size, activation='relu', input_shape=(self.train_x.shape[-1],)),
             tf.keras.layers.Dense(self.args.layer_size),
             #tf.keras.layers.Dropout(0.5),
             #tf.keras.layers.Dense(1, activation="sigmoid", bias_initializer=output_bias)
             tf.keras.layers.Dense(self.office_index.max_office_id + 1, activation="softmax")
        ])

        model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])

        model.fit(self.train_x, self.train_y, epochs=epochs_count,
                  workers=3,
                  batch_size=batch_size,
                  validation_split=0.2)
        res = model.evaluate(self.test_x, self.test_y)
        self.logger.info(res)

    def learn(self):
        self.learn_pool.check_uniq_trigram_heuristic()
        self.train_tensorflow()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be bigrams, learn")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--learn-pool", dest='learn_pool', default="office_declarator_pool.txt")
    parser.add_argument("--model-base", dest='model_base', required=False)
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    parser.add_argument("--layer-size", dest='layer_size', required=False, type=int, default=256)
    args = parser.parse_args()
    args.logger = setup_logging(log_file_name="predict_office.log")
    return args


def main():
    args = parse_args()
    if args.action == "bigrams":
        index = TOfficeIndex(args)
        index.build()
        index.write()
    elif args.action == "learn":
        assert args.model_base
        model = TPredictionModel(args)

        model.learn()
    else:
        raise Exception("unknown action")


if __name__ == '__main__':
    main()

