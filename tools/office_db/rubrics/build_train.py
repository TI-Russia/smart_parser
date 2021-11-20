from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory, TDeclarationWebSite
from office_db.rubrics import TOfficeRubrics

import matplotlib.pyplot as plt
import os
import re
import shutil
import string
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import losses
import re
import json
import argparse
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
import numpy as np
from tensorflow.keras.preprocessing import text_dataset_from_directory

def split_to_words(text):
    words = list()
    for r in re.split("[\s,\.;:_\"* ()«»/]", text.lower()):
        if len(r) > 1:
            if r not in {'http', 'https', 'www', 'ru', 'org'}:
                words.append(r)
    return words


def custom_standardization(input_data):
    words = split_to_words(input_data)
    return " ".join(words)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-train-pool", dest='output_train_pool', default="rubric_train_pool.txt")
    parser.add_argument("--output-model-path", dest='output_model_path')
    return parser.parse_args()


class TRawRecord:
    def __init__(self, rubric_id=None, name_words=None, web_name_words=None):
        self.rubric_id = rubric_id
        self.name_words = name_words
        self.web_name_words = web_name_words


class TRawPool:
    def __init__(self, logger, name):
        self.name = name
        self.logger = logger
        self.records = list()
        self.name_vocabulary = set()
        self.web_name_vocabulary = set()

    def add_record(self, record: TRawRecord):
        self.name_vocabulary.update(record.name_words)
        self.web_name_vocabulary.update(record.web_name_words)
        self.records.append(record)

    def to_ml_features(self):
        office_name_feat = list()
        web_name_feat = list()
        r: TRawRecord
        for r in self.records:
            office_name_feat.append(tf.constant(" ".join(r.name_words)))
            web_name_feat.append(tf.constant(" ".join(r.web_name_words)))
        return {
            "office_name_feat": office_name_feat,
            "web_site_feat": web_name_feat,
        }

    def to_ml_input(self):
        self.logger.info("build features for {} pool of {} cases".format(self.name, len(self.records)))
        labels = np.array(list(np.int32(c.rubric_id) for c in self.records))
        return self.to_ml_features(), labels


def create_train_pool(logger, file_name):
    offices = TOfficeTableInMemory()
    offices.read_from_local_file()
    office:  TOfficeInMemory
    pool = TRawPool(logger, "train")
    with open(file_name, "w") as outp:
        for office in offices.offices.values():
            if len(office.office_web_sites) > 0:
                r = TRawRecord(
                    rubric_id=office.rubric_id,
                    name_words=split_to_words(office.name),
                    web_name_words=split_to_words(office.office_web_sites[0].url),
                )
                if r.rubric_id is None:
                    continue
                outp.write(json.dumps(r.__dict__, ensure_ascii=False))
                pool.add_record(r)
    return pool


def build_text_layer(raw_vocab):
    vocabulary = tf.data.Dataset.from_tensor_slices(list(raw_vocab))
    embed_layer = TextVectorization(
        max_tokens=100,
        #standardize=custom_standardization,
        output_mode='int',
        output_sequence_length=100)
    embed_layer.adapt(vocabulary.batch(64))
    return embed_layer


def init_model_before_train(dense_layer_size, raw_pool: TRawPool):
    first_layers = list()
    second_layers = list()
    records_count = len(raw_pool.records)

    input_office_name_layer = tf.keras.Input(name="office_name_feat", shape=(1,), dtype=tf.string)
    first_layers.append(input_office_name_layer)
    office_name_layer = build_text_layer(raw_pool.name_vocabulary)
    second_layers.append(office_name_layer(input_office_name_layer))

    input_web_name_layer = tf.keras.Input(name="web_site_feat", shape=(1, ), dtype=tf.string)
    first_layers.append(input_web_name_layer)
    web_name_layer = build_text_layer(raw_pool.web_name_vocabulary)
    second_layers.append(web_name_layer(input_web_name_layer))

    concatenated_layer = tf.keras.layers.concatenate(second_layers)
    dense_layer1 = tf.keras.layers.Dense(dense_layer_size)(concatenated_layer)
    target_layer = tf.keras.layers.Dense(TOfficeRubrics.Other+1, name="target",
                                         activation="softmax")(dense_layer1)
    model = tf.keras.Model(
        inputs=first_layers,
        outputs=target_layer,
    )
    tf.keras.utils.plot_model(model, "predict_office.png", show_shapes=True)
    return model


def main():
    args = parse_args()
    logger = setup_logging("build_train")
    raw_pool = create_train_pool(logger, args.output_train_pool)
    train_x, train_y = raw_pool.to_ml_input()
    model = init_model_before_train(1024, raw_pool)
    logger.info("compile model...")
    model.compile(optimizer='adam',
                      loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                      metrics=['accuracy'])
    model.fit(train_x,
              train_y,
              epochs=20,
              workers=3,
              #batch_size=32,
              )
    logger.info("save to {}".format(args.output_model_path))
    model.save(args.output_model_path)


if __name__ == "__main__":
    main()

