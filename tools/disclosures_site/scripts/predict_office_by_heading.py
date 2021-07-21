from common.logging_wrapper import setup_logging
from common.russian_regions import TRussianRegions
from common.primitives import TUrlUtf8Encode

import tensorflow as tf
import json
import random
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
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
    #for w in words:
    #    yield w

    for w1, w2 in zip(words[:-1], words[1:]) :
        yield "_".join((w1, w2))


def get_trigrams(text):
    words = list(get_word_stems(text))

    for w1, w2, w3 in zip(words[:-2], words[1:-1], words[2:]) :
        yield "_".join((w1, w2, w3))


def reshape_to_category_feature(x, category_count):
    return tf.one_hot(x, category_count)
    dataframe = np.zeros((len(x), category_count))
    for index, found_categories in enumerate(x):
        for category_id in found_categories:
            dataframe[index][category_id] = 1.0
    return dataframe


class TDisclosuresConnection:
    def __init__(self, sql):
        self.connection = None
        self.sql = sql
        self.cursor = None

    def __enter__(self):
        self.connection = pymysql.connect(db="disclosures_db", user="disclosures", password="disclosures")
        self.cursor = self.connection.cursor()
        self.cursor.execute(self.sql)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.connection.close()


def build_web_site_to_offices():
    sql = """
        (
            select d.office_id, r.web_domain 
            from declarations_source_document d
            join declarations_web_reference r on r.source_document_id = d.id
        )
        union  (
            select d.office_id, r.web_domain 
            from declarations_source_document d
            join declarations_declarator_file_reference r on r.source_document_id = d.id
        )
    """

    with TDisclosuresConnection(sql) as conn:
        website_to_offices = defaultdict(set)
        for office_id, web_domain in conn.cursor:
            if TUrlUtf8Encode.is_idna_string(web_domain):
                web_domain = TUrlUtf8Encode.from_idna(web_domain)
            website_to_offices[web_domain].add(office_id)
    return website_to_offices


class TOfficeIndex:

    def __init__(self, args):
        self.args = args
        self.bigrams_index_by_str = None
        self.uniq_trigrams_to_office_id = None
        self.offices = None
        self.web_domains = None
        self.deterministic_web_domains = None

    def read(self):
        with open(self.args.bigrams_path) as inp:
            js = json.load(inp)
            self.bigrams_index_by_str = js['bigrams']
            self.uniq_trigrams_to_office_id = js['trigrams']
            self.offices = js['offices']
            self.web_domains = js['web_domains']
            self.deterministic_web_domains = js['deterministic_web_domains']
        self.args.logger.info("bigrams count = {}".format(len(self.bigrams_index_by_str)))

    def write(self):
        self.args.logger.info("write to {}".format(self.args.bigrams_path))
        with open(self.args.bigrams_path, "w") as outp:
            rec = {
                'bigrams': self.bigrams_index_by_str,
                'trigrams': self.uniq_trigrams_to_office_id,
                'offices': self.offices,
                'web_domains': self.web_domains,
                'deterministic_web_domains': self.deterministic_web_domains
            }
            json.dump(rec, outp, ensure_ascii=False, indent=4)

    def get_office_name(self, id):
        return self.offices[str(id)]['name']

    def get_office_region(self, id):
        return self.offices[str(id)]['region']

    def build_bigrams(self):
        self.args.logger.info("build bigrams")

        bigrams_to_office_ids = defaultdict(set)
        trigram_to_office_ids = defaultdict(set)
        self.offices = dict()
        sql = "select id, name, region_id from declarations_office"
        self.args.logger.info(sql)
        with TDisclosuresConnection(sql) as conn:
            for office_id, name, region_id in conn.cursor:
                if region_id is None:
                    region_id = 0
                self.offices[office_id] = {
                    'name': name,
                    'region': int(region_id),
                }
                if name.lower().startswith("сведения о"):
                    continue
                for b in get_bigrams(name):
                    bigrams_to_office_ids[b].add(office_id)
                for b in get_trigrams(name):
                    trigram_to_office_ids[b].add(office_id)
        pairs = enumerate(sorted(bigrams_to_office_ids.keys()))
        self.bigrams_index_by_str = dict((k, i) for (i, k) in pairs)
        self.args.logger.info("bigrams count = {}".format(len(self.bigrams_index_by_str)))
        self.uniq_trigrams_to_office_id = dict()
        for key, value in trigram_to_office_ids.items():
            if len(value) == 1:
                self.uniq_trigrams_to_office_id[key] = list(value)[0]
        self.args.logger.info("uniq_trigrams_to_office_id count = {}".format(len(self.uniq_trigrams_to_office_id)))

    def build_web_domains(self):
        self.args.logger.info("build web domains")
        web_domains = build_web_site_to_offices()
        self.deterministic_web_domains = dict()
        self.web_domains = dict()
        for web_domain, office_ids in web_domains.items():
            if len(office_ids) == 1:
                self.deterministic_web_domains[web_domain] = list(office_ids)[0]
            else:
                self.web_domains[web_domain] = len(self.web_domains)

    def build(self):
        self.build_bigrams()
        self.build_web_domains()


class TPredictionCase:
    def __init__(self, ml_model=None, sha256=None, web_domain=None, true_office_id=None, office_strings=None):
        self.ml_model = ml_model
        self.sha256 = sha256
        self.office_strings = office_strings
        self.web_domain = web_domain
        self.true_office_id = true_office_id

        self.text = self.get_text_from_office_strings()
        self.true_region_id = ml_model.office_index.get_office_region(self.true_office_id)

    def get_text_from_office_strings(self):
        if self.office_strings is None or len(self.office_strings) == 0:
            return ""
        office_strings = json.loads(self.office_strings)
        text = ""
        title = office_strings['title']
        if title is not None and len(title) > 0:
             text += office_strings['title'] + " "
        for t in office_strings['roles']:
            if len(t) > 0:
                text += t + " "
        for t in office_strings['departments']:
            if len(t) > 0:
                text += t + " "
        return text.strip()

    def from_json(self, js):
        js = json.loads(js)
        self.sha256 = js['sha256']
        self.web_domain = js['web_domain']
        self.true_office_id = js['true_office_id']
        self.office_strings = js['office_strings']
        self.true_region_id = self.ml_model.office_index.get_office_region(self.true_office_id)
        self.text = self.get_text_from_office_strings()

    def to_json(self, js):
        js = {
            'sha256': self.sha256,
            'web_domain': self.web_domain,
            'true_office_id': self.true_office_id,
            'office_strings': self.office_strings
        }
        return json.dumps(js, ensure_ascii=False)

    def get_bigrams_count(self):
        return len(self.ml_model.office_index.bigrams_index_by_str)

    def get_web_domains_count(self):
        return len(self.ml_model.office_index.web_domains)

    def get_bigram_feature(self):
        bigrams_one_hot = np.zeros(self.get_bigrams_count())
        for b in get_bigrams(self.text):
            bigram_id = self.ml_model.office_index.bigrams_index_by_str.get(b)
            if bigram_id is not None:
                bigrams_one_hot[bigram_id] = 1

        return bigrams_one_hot

    def get_web_domain_feature(self):
        web_domain_index = self.ml_model.office_index.web_domains.get(self.web_domain, 0)
        web_domain_one_hot = np.zeros(self.get_web_domains_count())
        web_domain_one_hot[web_domain_index] = 1
        return web_domain_one_hot

    def get_learn_target(self):
        if self.ml_model.learn_target_is_office:
            return self.true_office_id
        else:
            assert self.ml_model.learn_target_is_region
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
#mv "/tmp/docs.txt" ~/tmp/docs_and_titles
#cd ~/tmp/docs_and_titles
#cut -f 1  docs.txt >docs.txt.id
#python3 ~/smart_parser/tools/smart_parser_http/smart_parser_client.py --action office_strings --sha256-list docs.txt.id > docs_office_strings.txt
#paste docs.txt docs_office_strings.txt >office_declarator_pool.txt

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
                    sha256, web_domain, office_id, office_strings = line.strip().split("\t")
                    case = TPredictionCase(self.ml_model, sha256, web_domain, int(office_id), office_strings)
                    if len(case.text) == 0:
                        self.logger.debug("skip {} (empty text)".format(sha256))
                        continue
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
                outp.write("{}\n".format("\t".join([c.sha256, c.web_domain,  str(c.true_office_id), c.office_strings])))

    def split(self, train_pool_path, test_pool_path):
        random.shuffle(self.pool)
        train, test = train_test_split(self.pool, test_size=0.2)
        self.write_pool(train, train_pool_path)
        self.write_pool(test, test_pool_path)
        self.ml_model.logger.info("train size = {}, test size = {}".format(len(train), len(test)))

    def delete_deterministic_web_domains(self):
        new_pool = list()
        for c in self.pool:
            if c.web_domain in self.ml_model.office_index.deterministic_web_domains:
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
        self.learn_target_is_region = self.args.learn_target.startswith("region")
        self.train_pool = None

    def read_train(self):
        self.train_pool = TOfficePool(self, self.args.train_pool, row_count=self.args.row_count)
        assert len(self.train_pool.pool) > 0

    def read_test(self):
        self.test_pool = TOfficePool(self, self.args.test_pool, row_count=self.args.row_count)
        assert len(self.test_pool.pool) > 0

    def to_ml_input(self, cases, name):
        self.args.logger.info("build features for {} pool of {} cases".format(name, len(cases)))
        bigrams = np.array(list(c.get_bigram_feature() for c in cases))

        web_domains = np.array(list(c.get_web_domain_feature() for c in cases))
        features = {
            "text_feat": bigrams,
            "web_domain_feat": web_domains
        }

        labels = np.array(list(c.get_learn_target() for c in cases))
        return features, labels

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
            for case, (pred_target, pred_proba) in zip(cases, test_y_pred):
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

    def get_learn_target_count(self):
        if self.learn_target_is_office:
            return len(self.office_index.offices)
        else:
            assert self.learn_target_is_region
            return 111

    def init_model(self):
        bigrams_count = len(self.office_index.bigrams_index_by_str)
        text_input = tf.keras.Input(shape=(bigrams_count,), name="text_feat")

        web_domain_count = len(self.office_index.web_domains)
        web_domain_input = tf.keras.Input(shape=(web_domain_count,), name="web_domain_feat")
        concatenated_layer = tf.keras.layers.concatenate([text_input, web_domain_input])
        dense_layer = tf.keras.layers.Dense(self.args.layer_size, activation='relu')(concatenated_layer)
        target_layer = tf.keras.layers.Dense(self.get_learn_target_count(), name="target")(dense_layer)
        model = tf.keras.Model(
            inputs=[text_input, web_domain_input],
            outputs=target_layer,
        )
        tf.keras.utils.plot_model(model, "predict_office.png", show_shapes=True)
        return model

    def train_tensorflow(self):
        assert self.args.model_folder is not None
        #batch_size = 64
        batch_size =    256
        self.logger.info("train_tensorflow layer_size={}".format(self.args.layer_size))
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

    def build_handmade_regions(self, pool: TOfficePool):
        regions = TRussianRegions()
        y_true = list()
        y_pred = list()
        y_pred_proba = list()
        c: TPredictionCase
        for c in pool.pool:
            pred_region_id = regions.get_region_all_forms(c.text)
            if pred_region_id is None:
                pred_region_id = -1
            y_pred_proba.append((pred_region_id, 1))
            y_pred.append(pred_region_id)
            y_true.append(c.true_region_id)
        self.logger.info("accuracy = {} pool size = {}".format(accuracy_score(y_true, y_pred), len(y_true)))
        return y_pred_proba

    def test(self):
        if self.args.learn_target == "region_handmade":
            self.build_handmade_regions(self.test_pool)
        else:
            model = tf.keras.models.load_model(self.args.model_folder)
            test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
            res = model.evaluate(test_x, test_y)
            self.logger.info(res)

    def toloka(self):
        if self.args.learn_target == "region_handmade":
            test_y_pred = self.build_handmade_regions(self.test_pool)
            self.build_toloka_pool(self.test_pool.pool, test_y_pred, self.args.toloka_pool)
        else:
            model = tf.keras.models.load_model(self.args.model_folder)
            test_x, test_y = self.to_ml_input(self.test_pool.pool, "test")
            test_y_pred = model.predict(test_x)
            test_y_max = list()
            for pred_proba_y in test_y_pred:
                test_y_max.append( max(enumerate(pred_proba_y), key=operator.itemgetter(1)) )
            self.build_toloka_pool(self.test_pool.pool, test_y_max, self.args.toloka_pool)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', required=True, help="can be bigrams, train, test, toloka")
    parser.add_argument("--bigrams-path", dest='bigrams_path', required=False, default="office_ngrams.txt")
    parser.add_argument("--all-pool", dest='all_pool')
    parser.add_argument("--train-pool", dest='train_pool')
    parser.add_argument("--test-pool", dest='test_pool')
    parser.add_argument("--model-folder", dest='model_folder', required=False)
    parser.add_argument("--epoch-count", dest='epoch_count', required=False, type=int, default=10)
    parser.add_argument("--learn-target", dest='learn_target', required=False, default="office",
                        help="can be office, region, region_handmade",)
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

