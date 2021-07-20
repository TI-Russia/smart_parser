import random
import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
import re
from collections import defaultdict
from tensorflow.keras.preprocessing.sequence import pad_sequences


def get_word_stems(text):
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


def build_text_feature(cases, dct, batch_size=1):
    stem_index = dict((s, i) for i, s in enumerate(dct.keys()))
    features_list = list()
    max_seq_len = 10
    for text, region in cases:
        seq = list(stem_index[w] for w in get_word_stems(text))
        features_list.append(np.array(seq))
    #ds = tf.data.Dataset.from_tensor_slices({"stems": features_list})
    return {"stems": pad_sequences(features_list, max_seq_len)}


def reshape_to_category_feature(x, category_count=2):
    dataframe = np.zeros((len(x), category_count))
    for index, category_id in enumerate(x):
        dataframe[index][category_id] = 1.0
    return dataframe


def build_labels(cases):
    labels = list(region for text, region in cases)
    labels = reshape_to_category_feature (labels)
    return {"region": labels}


def init_model(optimizer, dict_size):
    # Variable-length sequence of ints
    text_input = tf.keras.Input(shape=(None,), name="stems")
    # Embed each word in the title into a 64-dimensional vector
    text_features = tf.keras.layers.Embedding(dict_size, 64)(text_input)
    # Reduce sequence of embedded words in the text into a single 128-dimensional vector
    text_features = tf.keras.layers.LSTM(128)(text_features)

    target_layer = tf.keras.layers.Dense(2, name="region")(text_features)

    model =  tf.keras.Model(
        inputs=[text_input],
        outputs=[target_layer],
    )

    tf.keras.utils.plot_model(model, "text_features.png", show_shapes=True)

    model.compile(optimizer=optimizer,
                  loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    print(model.summary())
    return model


def build_dictionary(train_cases,  test_cases):
    word_2_text = defaultdict(set)
    for text, _ in train_cases + test_cases:
        for w in get_word_stems(text):
            word_2_text[w].add(text)
    return word_2_text


def geo_classifier(train_cases, test_cases, epochs_count, optimizer='adam', batch_size=1):
    dct = build_dictionary(train_cases, test_cases)
    model = init_model(optimizer, len(dct))
    train_labels = build_labels(train_cases)
    test_labels = build_labels(test_cases)

    input_data = build_text_feature(train_cases, dct)
    model.fit(
        input_data,
        train_labels,
        epochs=epochs_count,
        batch_size=batch_size
    )
    input_data = build_text_feature(test_cases, dct)
    m = model.evaluate(
        input_data,
        test_labels
    )
    print(m)
    for (text, region), (c1, c2) in zip(test_cases, model.predict(input_data)):
        pred_region = 0 if c1 > c2 else 1
        if pred_region != region:
            print ("negative {} {} {}".format(text, c1, c2))
    return m[1]


train_cases = [
    ("мэр Москвы", 0),
    ("На юго-востоке Москвы столкнулись пять машин", 0),
    ("В Москве женщина бросила младенца в хостеле", 0),
    ("Собянин рассказал о ситуации с коронавирусом в Москве", 0),
    ("На юге Москвы нашли два тела", 0),
    ("ЧП в Москве: за убийством последовал суицид", 0),
    ("В Москве мужчина с женщиной выпали из окна многоэтажки и погибли", 0),
    ("В Кремле прокомментировали отмену QR-кодов в Москве", 0),
    ("Песков заявил об эффективности мер властей Москвы в борьбе с COVID", 0),
    ("В Москве нашли производителей поддельных справок о медотводе от прививки", 0),
    ("московские власти", 0),
    ("правительство города Москвы", 0),
    ("московский градоначальник", 0),
    ("Районы москвы", 0),
    ("В области самолетостроения Москва обогнала всех", 0),
    ("губернатор Самарской области", 1),
    ("Самарская область отметила День символик", 1),
    ("В Самарской области ужесточили ограничения по коронавирусу", 1),
    ("За 22 троллейбуса «Адмирал» Самарская область будет ...", 1),
    ("«Все оттенки Жигулевского»: чем Самарская область", 1),
    ("Самарская область усилит контроль за ограничениями по коронавирусу", 1),
    ("В Самарской области ужесточат коронавирусные", 1),
    ("Самарская область выплатила 15 млн руб. по 28-му купону", 1),
    ("Вывоз отходов обеспечили для 99% населения Самарской области, ", 1),
    ("Скончался бывший руководитель СУ СК по Самарской области", 1),
    ("мэр Самары и губернаторо Самарской области", 1),
    ("В Самаркой области женщина бросила младенца в хостеле", 1),
    ("Собянин рассказал о ситуации с коронавирусом в Самарской области", 1),
    ("Иван Московский стал начальников Самарской области", 1),
    ("Московский райой Самарской области", 1),
    ("В", 1),
]

test_cases = [
    ("Москва - город герой", 0),
    ("уехал из Москвы", 0),
    ("мерия Москвы", 0),
    ("Я думаю о Москве", 0),
    ("я живу  в Самарской области", 1),
    ("приехал  в Самарскую область", 1),
    ("налоговая по Самарской области закончила проверку", 1),
    ("под Самарской областью нашли золото", 1),

    # hard cases
    ("парень из Московского района самарской области", 1),
    ("парень из Ростовского района самарской области", 1),
    ("самарская улица в городе Москве", 0)
]

accuracy = geo_classifier(train_cases, test_cases, 20)
assert accuracy == 1.0

