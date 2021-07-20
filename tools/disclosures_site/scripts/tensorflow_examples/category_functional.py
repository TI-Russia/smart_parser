import random
import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'


def prepare_dataset(category_count, x, labels, batch_size):
    dataframe = np.zeros((len(x), category_count ))
    for index, category_id in enumerate(x):
        dataframe[index][category_id] = 1.0

    ds = tf.data.Dataset.from_tensor_slices((dataframe, labels))
    ds = ds.batch(batch_size)
    return ds


def categorial_tf(category_count, train_size, epochs_count, optimizer='adam', batch_size=1):
    all_categories = list(range(0, category_count))
    train_data = all_categories * int(train_size / category_count)
    random.shuffle(train_data)
    train_dataset = prepare_dataset(category_count, train_data, train_data, batch_size=batch_size)

    test_data = all_categories
    test_dataset = prepare_dataset(category_count, test_data, test_data, batch_size=batch_size)

    inputs = tf.keras.Input(shape=(category_count,))
    dense = tf.keras.layers.Dense(category_count, activation="relu")
    x = dense(inputs)
    #x = tf.keras.layers.Dense(category_count, activation="relu")(x)
    outputs = tf.keras.layers.Dense(category_count)(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="cat_model_{}".format(category_count))

    model.compile(optimizer=optimizer,
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    print(model.summary())
    model.fit(
        train_dataset,
        epochs=epochs_count,
        validation_data=test_dataset,
    )
    m = model.evaluate(test_dataset)
    print(m)
    return m[1]


#accuracy = categorial_tf(3, 50, 30)
#assert accuracy == 1.0

#accuracy = categorial_tf(10, 50, 30)
#assert accuracy == 1.0

#accuracy = categorial_tf(100, 500, 30)
#assert accuracy == 1.0

accuracy = categorial_tf(1000, 5000, 30, batch_size=10)
assert accuracy == 1.0
