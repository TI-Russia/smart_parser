import numpy as np
import pandas as pd

import tensorflow as tf
from tensorflow import feature_column
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
import pathlib


csv_file = '/home/sokirko/smart_parser/tools/disclosures_site/new_car_cases.txt.6'
source_dataframe = pd.read_json(csv_file, lines=True, nrows=1000)
print(source_dataframe.head())

dataframe = pd.DataFrame()
dataframe['target'] = np.where(source_dataframe['positive'], 1, 0)
dataframe['income_diff'] = source_dataframe['previous_year_income'] / (source_dataframe['year_income'] + 0.0000001)
dataframe['spouse_income_diff'] = source_dataframe['spouse_previous_year_income'] / (source_dataframe['spouse_year_income'] + 0.0000001)
dataframe['gender'] = source_dataframe['gender'].apply(lambda x: int(x) if not np.isnan(x) else 0)
dataframe['rubric_id'] = source_dataframe['rubric_id'].apply(lambda x: int(x) if not np.isnan(x) else 0)
dataframe['region_id'] = source_dataframe['region_id'].apply(lambda x: int(x) if not np.isnan(x) else 0)
dataframe['year_income'] = source_dataframe['year_income']
dataframe['year'] = source_dataframe['year']
dataframe['square_sum'] = source_dataframe['declarant_real_estate'].apply(lambda x: x['square_sum'])
dataframe['spouse_square_sum'] = source_dataframe['spouse_real_estate'].apply(lambda x: x['square_sum'])

train, test = train_test_split(dataframe, test_size=0.2)
train, val = train_test_split(train, test_size=0.2)
print(len(train), 'train examples')
print(len(val), 'validation examples')
print(len(test), 'test examples')



# A utility method to create a tf.data dataset from a Pandas Dataframe
def df_to_dataset(dataframe, shuffle=True, batch_size=32):
    dataframe = dataframe.copy()
    labels = dataframe.pop('target')
    ds = tf.data.Dataset.from_tensor_slices((dict(dataframe), labels))
    if shuffle:
        ds = ds.shuffle(buffer_size=len(dataframe))
    ds = ds.batch(batch_size)
    return ds


feature_columns = []

for header in ['income_diff', 'spouse_income_diff', 'year_income', 'square_sum', 'spouse_square_sum']:
    feature_columns.append(feature_column.numeric_column(header))


for col_name in ['year', 'gender', 'rubric_id', 'region_id']:
    categorical_column = feature_column.categorical_column_with_vocabulary_list(col_name, dataframe[col_name].unique())
    indicator_column = feature_column.indicator_column(categorical_column)
    feature_columns.append(indicator_column)

feature_layer = tf.keras.layers.DenseFeatures(feature_columns)

batch_size = 32
train_ds = df_to_dataset(train, batch_size=batch_size)
val_ds = df_to_dataset(val, shuffle=False, batch_size=batch_size)
test_ds = df_to_dataset(test, shuffle=False, batch_size=batch_size)

model = tf.keras.Sequential([
  feature_layer,
  layers.Dense(128, activation='relu'),
  layers.Dense(128, activation='relu'),
  layers.Dropout(.1),
  ##layers.Dense(2, activation="softmax")  <- does not work
  layers.Dense(1)
])

model.compile(optimizer='adam',
              loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
              metrics=['accuracy'])

model.fit(train_ds,
          validation_data=val_ds,
          epochs=10,
          class_weight={0:1, 1:5})


loss, accuracy = model.evaluate(test_ds)
print("Accuracy", accuracy)

res =  model.predict(test_ds)
#print(res)

print(train_ds['target'])