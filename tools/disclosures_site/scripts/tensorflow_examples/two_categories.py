import random
import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'


def reshape_to_category_feature(x, category_count=2):
    dataframe = np.zeros((len(x), category_count))
    for index, category_id in enumerate(x):
        dataframe[index][category_id] = 1.0
    return dataframe


def reshape_input(cat1, cat2):
    return {
        'cat1': reshape_to_category_feature(cat1),
        'cat2': reshape_to_category_feature(cat2),
    }


def build_labels(cat1, cat2):
    return reshape_to_category_feature(list(int(c1 + c2 > 0) for c1, c2 in zip(cat1, cat2)))


def init_model(optimizer):
    cat1_input = tf.keras.Input(shape=(2,), name="cat1")
    cat2_input = tf.keras.Input(shape=(2,), name="cat2")
    concated_layer = tf.keras.layers.concatenate([cat1_input, cat2_input])
    target_layer = tf.keras.layers.Dense(2, name="target")(concated_layer)

    model =  tf.keras.Model(
        inputs=[cat1_input, cat2_input],
        outputs=target_layer,
    )

    tf.keras.utils.plot_model(model, "multi_input_and_output_model.png", show_shapes=True)

    model.compile(optimizer=optimizer,
                  loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    print(model.summary())
    return model


def binary_or(train_size, epochs_count, optimizer='adam', batch_size=1):
    model = init_model(optimizer)

    train_cat1 = list(random.randint(0, 1) for i in range(train_size))
    train_cat2 = list(random.randint(0, 1) for i in range(train_size))
    train_labels = build_labels(train_cat1, train_cat2)

    test_cat1 = [0, 1, 1, 0]
    test_cat2 = [0, 1, 0, 1]
    test_labels = build_labels(test_cat1, test_cat2)

    input_data = reshape_input(train_cat1, train_cat2)
    model.fit(
        input_data,
        {
          'target': train_labels,
        },
        epochs=epochs_count,
        batch_size=batch_size
    )
    m = model.evaluate(reshape_input(test_cat1, test_cat2), {"target": test_labels})
    print(m)
    return m[1]


accuracy = binary_or(100, 30)
assert accuracy == 1.0

