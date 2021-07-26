import random
import tensorflow as tf


def df_to_dataset(dataframe, batch_size):
    dataframe = dataframe.copy()
    labels = dataframe.pop('target')
    ds = tf.data.Dataset.from_tensor_slices((dataframe, labels))
    ds = ds.batch(batch_size)
    return ds


def categorial_tf(category_count, train_size, epochs_count, optimizer='adam', batch_size=1):
    data = list(random.randint(0, category_count - 1) for i in range(train_size))

    train_data = {
        "feat_1": data,
        "target": data
    }
    test_data = {
        "feat_1": list(range(0, category_count)),
        "target": list(range(0, category_count)),
    }

    train_dataset = df_to_dataset(train_data, batch_size=batch_size)
    test_dataset = df_to_dataset(test_data, batch_size=batch_size)

    feat_1 = tf.feature_column.numeric_column('feat_1')
    feature_layer = tf.keras.layers.DenseFeatures([feat_1])

    model = tf.keras.Sequential([
        feature_layer,
        tf.keras.layers.Dense(category_count, activation='relu'),
        tf.keras.layers.Dense(category_count, activation='relu'),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(category_count)
    ])

    model.compile(optimizer=optimizer,
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])

    model.fit(
        train_dataset,
        epochs=epochs_count,
        validation_data=test_dataset,
    )
    m = model.evaluate(test_dataset)
    print(m)
    return m[1]


accuracy = categorial_tf(
    category_count=3,
    train_size=200,
    epochs_count=100,
    optimizer="SGD",
    batch_size=1)
assert accuracy == 1.0

#accuracy = categorial_tf(10, 500, 50)
#assert accuracy == 1.0

#accuracy = categorial_tf(10, 50, 500)
#assert accuracy == 1.0