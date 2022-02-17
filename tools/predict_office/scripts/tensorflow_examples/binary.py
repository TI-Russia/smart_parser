import tensorflow as tf


def df_to_dataset(dataframe, shuffle=True, batch_size=32):
    dataframe = dataframe.copy()
    labels = dataframe.pop('target')
    ds = tf.data.Dataset.from_tensor_slices((dataframe, labels))
    #if shuffle:
    #    ds = ds.shuffle(buffer_size=len(dataframe))
    ds = ds.batch(batch_size)
    return ds


def binary_tf():
    train_data = {
        "feat_1": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "target": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    }
    test_data = {
        "feat_1": [1, 0],
        "target": [1, 0]
    }

    train_dataset = df_to_dataset(train_data, batch_size=3)
    test_dataset = df_to_dataset(test_data, batch_size=3)

    feat_1 = tf.feature_column.numeric_column('feat_1')
    feature_layer = tf.keras.layers.DenseFeatures([feat_1])

    model = tf.keras.Sequential([
        feature_layer,
        tf.keras.layers.Dense(1, activation='linear'),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(1)
    ])

    model.compile(#optimizer='adam',
                  optimizer='SGD',
                  #optimizer='Ftrl',
                  loss=tf.keras.losses.MeanAbsoluteError(),
                  metrics=['accuracy'])

    model.fit(train_dataset, epochs=150)
    m = model.evaluate(test_dataset)
    print(m)
    print(model.predict(test_dataset))

binary_tf()
