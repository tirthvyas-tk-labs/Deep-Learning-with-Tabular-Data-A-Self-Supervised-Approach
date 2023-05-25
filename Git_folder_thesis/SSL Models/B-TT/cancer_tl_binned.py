# -*- coding: utf-8 -*-
"""Cancer_TL_binned.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rsofcLTcdj4qBoQ-x37JX5TxJWNrWGK9
"""

pip install -U tensorflow-addons

# Commented out IPython magic to ensure Python compatibility.
## Import dependencies 
import numpy as np
import pandas as pd
import scipy as sp

import matplotlib.pyplot as plt 
# %matplotlib inline
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

import os
import pathlib
import gc
import sys
import re
import math 
import random
import functools
import time 
import datetime as dt
from tqdm import tqdm 

import sklearn
from sklearn.model_selection import KFold, StratifiedKFold

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import tensorflow_addons as tfa

import warnings
warnings.filterwarnings('ignore')

print('import done!')

exp_config = {'gpu': True,
              'tf_memory_limit': True,
              'n_bins': 64,
              'mask_ratio': 0.2,
              'mask_token': -100,
              'batch_size': 512,
              'val_size': 2_000,
              'learning_rate': 5e-3,
              'weight_decay': 0.0001,
              'train_epochs': 10,
              'checkpoint_filepath': './tmp/model/exp.ckpt',
             }

model_config = {'embedding_dim': 24,
                'num_transformer_blocks': 6,
                'num_heads': 3,
                'tf_dropout_rates': [0., 0., 0., 0., 0., 0.,],
                'ff_dropout_rates': [0., 0., 0., 0., 0., 0.,],
                'mlp_dropout_rates': [0., 0.1],
                'mlp_hidden_units_factors': [4, 4],
               }

print('Parameters setted!')

# importing libraries
import pandas as pd
import numpy as np
# loading the dataset
trainDF = pd.read_csv("https://raw.githubusercontent.com/tirthvyas-tk-labs/Housing_dataset/main/breast_cancer_dataset.csv")

trainDF

trainDF = trainDF.drop(columns = ['id', 'Unnamed: 32'])

trainDF

MainDF = trainDF.copy()

# Have droped the null values as they are very small
MainDF.dropna(inplace=True)
MainDF.isna().sum()
print(MainDF.shape)
MainDF.head()

from sklearn.preprocessing import LabelEncoder

ocean_le = LabelEncoder()
MainDF['diagnosis'] = ocean_le.fit_transform(MainDF['diagnosis'])

ocean_le.classes_

MainDF.info()

from sklearn.model_selection import train_test_split

cancer_60, cancer_40 = train_test_split(MainDF, test_size=0.4, random_state=42)

cancer_60

cancer_60.columns

numerical_features = ['radius_mean', 'texture_mean', 'perimeter_mean',
       'area_mean', 'smoothness_mean', 'compactness_mean', 'concavity_mean',
       'concave points_mean', 'symmetry_mean', 'fractal_dimension_mean',
       'radius_se', 'texture_se', 'perimeter_se', 'area_se', 'smoothness_se',
       'compactness_se', 'concavity_se', 'concave points_se', 'symmetry_se',
       'fractal_dimension_se', 'radius_worst', 'texture_worst',
       'perimeter_worst', 'area_worst', 'smoothness_worst',
       'compactness_worst', 'concavity_worst', 'concave points_worst',
       'symmetry_worst', 'fractal_dimension_worst']

categorical_features = ['diagnosis']

cancer_60_bin_data = cancer_60.copy()

# Binning is used to transform a continuous or numerical variable into a categorical feature.
# As our TabTransformer will be taking only categorical values for training so have converted the values to categorical.

def binning_numerical(dataframe, numerical, n_bins=20):
    df = dataframe.copy()
    for nc in numerical:
        df[nc] = pd.cut(df[nc], bins=n_bins, labels=False)
    return df

n_bins = exp_config['n_bins']
cancer_60_bin_data = binning_numerical(cancer_60_bin_data, numerical_features, n_bins=n_bins)

cancer_60_bin_data

categorical_features = ['diagnosis', 'radius_mean', 'texture_mean', 'perimeter_mean',
       'area_mean', 'smoothness_mean', 'compactness_mean', 'concavity_mean',
       'concave points_mean', 'symmetry_mean', 'fractal_dimension_mean',
       'radius_se', 'texture_se', 'perimeter_se', 'area_se', 'smoothness_se',
       'compactness_se', 'concavity_se', 'concave points_se', 'symmetry_se',
       'fractal_dimension_se', 'radius_worst', 'texture_worst',
       'perimeter_worst', 'area_worst', 'smoothness_worst',
       'compactness_worst', 'concavity_worst', 'concave points_worst',
       'symmetry_worst', 'fractal_dimension_worst']

cancer_60_scaled_data = cancer_60.copy()

from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# create an instance of the StandardScaler
scaler = MinMaxScaler()

# fit the scaler to your data and transform it
scaled_data = scaler.fit_transform(cancer_60_scaled_data)

# create a pandas dataframe from the scaled data
cancer_60_scaled_data = pd.DataFrame(scaled_data, columns=cancer_60_scaled_data.columns)

display(cancer_60_scaled_data)

data_bin_df = cancer_60_bin_data.copy()

source_domain_male_df_scaled = cancer_60_scaled_data.copy()

# Train valid split
val_size = exp_config['val_size']

# valid_data = data_bin_df[:val_size]
train_data = data_bin_df

# valid_label = source_domain_male_df_scaled[:val_size]
train_label = source_domain_male_df_scaled

print("train_data: " ,len(train_data))
# print("valid_data: " ,len(valid_data))
print("train_label: " ,len(train_label))
# print("valid_label: " ,len(valid_label))

# Creating training dataset, where I have performed the process of MASKING.
# Where the MASKED values are replaced 1 and other values by 0. 
# And the masked parts on input data are replaced with the mask_tokens.

def create_train_dataset(data_df,
                         target_df,
                         categorical_features,
                         mask_ratio=0.2,
                         mask_token=-100,
                         batch_size=128, 
                         shuffle=True,
                         repeat=False,
                         drop_remainder=False,
                         return_sample_weight=True):
    
    data_df = data_df
    data_values = data_df.values
    
    target_df = target_df
    target = target_df.values
    
    # Masking
    mask = np.random.random_sample(size=target.shape) 
    mask = np.where(mask < mask_ratio, 1, 0)
    
    # Tokens
    train_data = np.where(mask==1, mask_token, data_values)  
    
    train_data = train_data.astype(np.float64)
    target = target.astype(np.float64)
    
    data = {}
    for i, cf in enumerate(categorical_features):
        data[cf] = train_data[:, i]
        
    if return_sample_weight:
        sample_weight = mask.astype(np.float64) # Here only masked parts are considered in loss calculation.
        sample_weight = np.expand_dims(sample_weight, -1)
        ds = tf.data.Dataset.from_tensor_slices((data, target, sample_weight))
    else:
        ds = tf.data.Dataset.from_tensor_slices((data, target))
    
    if shuffle:
        if len(data_df) < 1000:
            buffer_size = len(data_df)
        else:
            buffer_size = 1000
        ds = ds.shuffle(buffer_size=buffer_size)
    if repeat:
        ds = ds.repeat()
    ds = ds.batch(batch_size, drop_remainder=drop_remainder)
    ds = ds.prefetch(batch_size)
    
    return ds

# Creating datasets for loading in the model

mask_ratio = exp_config['mask_ratio']
batch_size = exp_config['batch_size']
mask_token = exp_config['mask_token']

train_ds = create_train_dataset(train_data, 
                                train_label,
                                categorical_features,
                                mask_ratio=mask_ratio,
                                mask_token=mask_token,
                                batch_size=batch_size,
                                shuffle=True,
                                repeat=True,
                                drop_remainder=True,
                                return_sample_weight=True)

example_data, example_labels, example_sample_weight = next(train_ds.take(1).as_numpy_iterator())

for key in example_data:
    print(f'{key}, shape:{example_data[key].shape}, {example_data[key].dtype}')
    
print(f'labels shape: {example_labels.shape}')
print(f'sample_wegihts shape: {example_sample_weight.shape}')

def create_preprocessing_model(categorical, df, mask_token=-100):
    ## Create input layers
    preprocess_inputs = {}
    for c in categorical:
        preprocess_inputs[c] = layers.Input(shape=(1,),
                                             dtype=np.float64)
    
    ## Create preprocess layers        
    lookup_layers = {}
    for c in categorical:
        lookup_layers[c] = layers.IntegerLookup(vocabulary=df[c].unique(),
                                            mask_token=mask_token,
                                            output_mode='int')
                
    ## Create outputs
    preprocess_outputs = {}
    for c in categorical:
        preprocess_outputs[c] = lookup_layers[c](preprocess_inputs[c])
            
    ## Create model
    preprocessing_model = tf.keras.Model(preprocess_inputs,
                                         preprocess_outputs)
    
    return preprocessing_model, lookup_layers

## Create preprocessing model
preprocessing_model, lookup_layers = create_preprocessing_model(
    categorical_features, train_data, mask_token=mask_token)

## Apply the preprocessing model in tf.data.Dataset.map
train_ds = train_ds.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)


## Display a preprocessed input sample
example_data = next(train_ds.take(1).as_numpy_iterator())[0]
for key in example_data:
    print(f'{key}, shape: {example_data[key].shape}, {example_data[key].dtype}')

def TabTransformer(categorical, lookup_layers, 
                          tf_dropout_rates, 
                          ff_dropout_rates,
                          mlp_hidden_units_factors=[2, 1],
                          mlp_dropout_rates=[0., 0.],
                          embedding_dim=12,
                          num_transformer_blocks=6, 
                          num_heads=3,):
    
    ## Create input layers
    model_inputs = {key: layers.Input(shape=(1,),
                                      dtype='float64') for key in categorical}
    
    ## Create Embeddings for categorical features
    encoded_feature_list = []
    for key in model_inputs:
        embedding = layers.Embedding(input_dim=lookup_layers[key].vocabulary_size(),
                                     output_dim=embedding_dim)
        encoded_feature = embedding(model_inputs[key])
        encoded_feature_list.append(encoded_feature)
    encoded_features = tf.concat(encoded_feature_list, axis=1)
    
    for block_idx in range(num_transformer_blocks):
        ## Create a multi-head attention layer
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=embedding_dim,
            dropout=tf_dropout_rates[block_idx],
            name=f'multi-head_attention_{block_idx}'
        )(encoded_features, encoded_features)
        ## Skip connection 1
        x = layers.Add(
            name=f'skip_connection1_{block_idx}'
        )([attention_output, encoded_features])
        ## Layer normalization 1
        x = layers.LayerNormalization(
            name=f'layer_norm1_{block_idx}', 
            epsilon=1e-6
        )(x)
        ## Feedforward
        feedforward_output = keras.Sequential([
            layers.Dense(embedding_dim, activation=keras.activations.gelu),
            layers.Dropout(ff_dropout_rates[block_idx]),
        ], name=f'feedforward_{block_idx}'
        )(x)
        ## Skip_connection 2
        x = layers.Add(
            name=f'skip_connection2_{block_idx}'
        )([feedforward_output, x])
        ## Layer normalization 2
        encoded_features = layers.LayerNormalization(
            name=f'layer_norm2_{block_idx}', 
            epsilon=1e-6
        )(x)
        
    mlp_layers = []
    mlp_hidden_units = [
        int(factor * encoded_features.shape[-1]) for factor in mlp_hidden_units_factors]
    
    for i, units in enumerate(mlp_hidden_units):
        mlp_layers.append(layers.BatchNormalization())
        mlp_layers.append(layers.Dense(units,
                                       activation=keras.activations.selu))
        mlp_layers.append(layers.Dropout(mlp_dropout_rates[i]))
    mlp_layers.append(layers.Dense(1, activation=None))
    model_outputs = keras.Sequential(mlp_layers, name='MLP')(encoded_features)
    # model_outputs = tf.squeeze(model_outputs)
    
    ## Create model
    training_model = keras.Model(inputs=model_inputs,
                                 outputs=model_outputs)
    
    return training_model

# Settings for TabTransformer

tf_dropout_rates = model_config['tf_dropout_rates']
ff_dropout_rates = model_config['ff_dropout_rates']
embedding_dim = model_config['embedding_dim']
num_transformer_blocks = model_config['num_transformer_blocks']
num_heads = model_config['num_heads']
mlp_dropout_rates = model_config['mlp_dropout_rates']
mlp_hidden_units_factors = model_config['mlp_hidden_units_factors']

# Creating TabTransformer
training_model = TabTransformer(categorical_features,
                                       lookup_layers,
                                       tf_dropout_rates=tf_dropout_rates, 
                                       ff_dropout_rates=ff_dropout_rates,
                                       mlp_hidden_units_factors=mlp_hidden_units_factors,
                                       mlp_dropout_rates=mlp_dropout_rates,
                                       embedding_dim=embedding_dim,
                                       num_transformer_blocks=num_transformer_blocks,
                                       num_heads=num_heads,
                                       )

# Model FLow
keras.utils.plot_model(training_model, show_shapes=True, rankdir="LR")

# Learning rate finder

class LRFind(tf.keras.callbacks.Callback):
    def __init__(self, min_lr, max_lr, n_rounds):
        self.min_lr = min_lr
        self.max_lr = max_lr
        self.step_up = tf.constant((max_lr / min_lr) ** (1 / n_rounds))
        self.lrs = []
        self.losses = []

    def on_train_begin(self, logs=None):
        self.weights = self.model.get_weights()
        self.model.optimizer.lr = self.min_lr

    def on_train_batch_end(self, batch, logs=None):
        self.lrs.append(self.model.optimizer.lr.numpy())
        self.losses.append(logs['loss'])
        self.model.optimizer.lr = self.model.optimizer.lr * self.step_up
        if self.model.optimizer.lr > self.max_lr:
            self.model.stop_training = True 

    def on_train_end(self, logs=None):
        self.model.set_weights(self.weights)

# Model compiling and building 

## Settings for Training
epochs = exp_config['train_epochs']
batch_size = exp_config['batch_size']
steps_per_epoch = len(train_data)//batch_size 

## Model compile
learning_rate = exp_config['learning_rate']
weight_decay = exp_config['weight_decay']

learning_schedule = tf.keras.optimizers.schedules.CosineDecay(
    initial_learning_rate=learning_rate,
    decay_steps=epochs*steps_per_epoch, 
    alpha=0.0)

optimizer = tfa.optimizers.AdamW(
    learning_rate=learning_schedule,
    weight_decay=weight_decay)

loss_fn = keras.losses.MeanSquaredError()

training_model.compile(optimizer=optimizer,
                       loss=loss_fn,
                       metrics=[keras.metrics.RootMeanSquaredError(),
                                keras.metrics.MeanAbsoluteError()])

training_model.summary()

min_lr = 1e-6 # minimum learning rate
max_lr = 1e-1 # maximum learning rate
lr_find_epochs = 1
lr_find_steps = 200
lr_find_batch_size = 512

lr_find = LRFind(min_lr, max_lr, lr_find_steps)

## Model compile
learning_rate = exp_config['learning_rate']
weight_decay = exp_config['weight_decay']

learning_schedule = tf.keras.optimizers.schedules.CosineDecay(
    initial_learning_rate=learning_rate,
    decay_steps=epochs*steps_per_epoch, 
    alpha=0.0)

optimizer = tfa.optimizers.AdamW(
    learning_rate=learning_schedule,
    weight_decay=weight_decay)

loss_fn = keras.losses.MeanSquaredError()

## Finding Learning rate
training_model.compile(optimizer=optimizer,
                       loss=loss_fn,
                       metrics=[keras.metrics.RootMeanSquaredError(),
                                keras.metrics.MeanAbsoluteError()])

training_model.fit(train_ds,
                   steps_per_epoch=lr_find_steps,
                   epochs=lr_find_epochs,
                   callbacks=[lr_find])

plt.plot(lr_find.lrs, lr_find.losses)
plt.xscale('log')
plt.show()

# make all layers untrainable by freezing weights (except for last layer)
for l, layer in enumerate(training_model.layers):
    layer.trainable = False

training_model.summary()

inputs = training_model.input

x = training_model.output
x = keras.layers.Dense(1, activation='sigmoid')(x)
outputs = tf.squeeze(x)

model_2 = keras.models.Model(inputs=inputs, outputs=outputs)

model_2.summary()

cancer_40

cancer_40.columns

categorical_features = ['diagnosis']

numerical_features = ['radius_mean', 'texture_mean', 'perimeter_mean',
       'area_mean', 'smoothness_mean', 'compactness_mean', 'concavity_mean',
       'concave points_mean', 'symmetry_mean', 'fractal_dimension_mean',
       'radius_se', 'texture_se', 'perimeter_se', 'area_se', 'smoothness_se',
       'compactness_se', 'concavity_se', 'concave points_se', 'symmetry_se',
       'fractal_dimension_se', 'radius_worst', 'texture_worst',
       'perimeter_worst', 'area_worst', 'smoothness_worst',
       'compactness_worst', 'concavity_worst', 'concave points_worst',
       'symmetry_worst', 'fractal_dimension_worst']

cancer_40_bin_data = cancer_40.copy()

# Binning is used to transform a continuous or numerical variable into a categorical feature.
# As our TabTransformer will be taking only categorical values for training so have converted the values to categorical.

def binning_numerical(dataframe, numerical, n_bins=20):
    df = dataframe.copy()
    for nc in numerical:
        df[nc] = pd.cut(df[nc], bins=n_bins, labels=False)
    return df

n_bins = exp_config['n_bins']
cancer_40_bin_data = binning_numerical(cancer_40_bin_data, numerical_features, n_bins=n_bins)

categorical_features = ['radius_mean', 'texture_mean', 'perimeter_mean',
       'area_mean', 'smoothness_mean', 'compactness_mean', 'concavity_mean',
       'concave points_mean', 'symmetry_mean', 'fractal_dimension_mean',
       'radius_se', 'texture_se', 'perimeter_se', 'area_se', 'smoothness_se',
       'compactness_se', 'concavity_se', 'concave points_se', 'symmetry_se',
       'fractal_dimension_se', 'radius_worst', 'texture_worst',
       'perimeter_worst', 'area_worst', 'smoothness_worst',
       'compactness_worst', 'concavity_worst', 'concave points_worst',
       'symmetry_worst', 'fractal_dimension_worst']

cancer_40_scaled_data = cancer_40.copy()

from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# create an instance of the StandardScaler
scaler = MinMaxScaler()

# fit the scaler to your data and transform it
scaled_data = scaler.fit_transform(cancer_40_scaled_data)

# create a pandas dataframe from the scaled data
cancer_40_scaled_data = pd.DataFrame(scaled_data, columns=cancer_40_scaled_data.columns)

display(cancer_40_scaled_data)

from sklearn.model_selection import train_test_split

supervised_90_percent_target_domain_female, supervised_10_percent_target_domain_female = train_test_split(cancer_40, test_size=0.5, random_state=42)

print("Number of samples in 10% portion:", len(supervised_10_percent_target_domain_female))
print("Number of samples in 90% portion:", len(supervised_90_percent_target_domain_female))

bin_supervised_90_percent_target_domain_female, bin_supervised_10_percent_target_domain_female = train_test_split(cancer_40_bin_data, test_size=0.5, random_state=42)

print("Number of samples in 10% portion:", len(bin_supervised_10_percent_target_domain_female))
print("Number of samples in 90% portion:", len(bin_supervised_90_percent_target_domain_female))

X = bin_supervised_10_percent_target_domain_female
y = supervised_10_percent_target_domain_female['diagnosis']

y

X_test = bin_supervised_90_percent_target_domain_female
y_test = supervised_90_percent_target_domain_female['diagnosis']

y_test

train_data_10_percent = X
target_data_10_percent = y

test_data_90_percent = X_test
test_target_data_90_percent = y_test

print("train_data: " ,len(train_data_10_percent))
print("target_data: " ,len(target_data_10_percent))

print("test_data: " ,len(test_data_90_percent))
print("test_target_data: " ,len(test_target_data_90_percent))

categorical_features_10_90 = ['diagnosis','radius_mean', 'texture_mean', 'perimeter_mean',
       'area_mean', 'smoothness_mean', 'compactness_mean', 'concavity_mean',
       'concave points_mean', 'symmetry_mean', 'fractal_dimension_mean',
       'radius_se', 'texture_se', 'perimeter_se', 'area_se', 'smoothness_se',
       'compactness_se', 'concavity_se', 'concave points_se', 'symmetry_se',
       'fractal_dimension_se', 'radius_worst', 'texture_worst',
       'perimeter_worst', 'area_worst', 'smoothness_worst',
       'compactness_worst', 'concavity_worst', 'concave points_worst',
       'symmetry_worst', 'fractal_dimension_worst']

def create_train_dataset_10_90(data_df,
                            target_df,
                            categorical_features_10_90,
                            batch_size=128,
                            shuffle=True,
                            repeat=False,
                            drop_remainder=False,
                            return_sample_weight=True):
    # Get the data and target values
    data_values = data_df.values.astype(np.float64)
    target = target_df.values.astype(np.float64)

    # Split the data into dictionary of categorical features and numerical features
    data = {}
    for i, cf in enumerate(categorical_features_10_90):
        data[cf] = data_values[:, i]

    # Create the dataset
    if return_sample_weight:
        # Here all the parts of data are considered in loss calculation.
        sample_weight = np.ones_like(target, dtype=np.float64)
        sample_weight = np.expand_dims(sample_weight, -1)
        ds = tf.data.Dataset.from_tensor_slices((data, target, sample_weight))
    else:
        ds = tf.data.Dataset.from_tensor_slices((data, target))

    # Shuffle and batch the dataset
    if shuffle:
        if len(data_df) < 1000:
            buffer_size = len(data_df)
        else:
            buffer_size = 1000
        ds = ds.shuffle(buffer_size=buffer_size)
    if repeat:
        ds = ds.repeat()
    ds = ds.batch(batch_size, drop_remainder=drop_remainder)
    ds = ds.prefetch(batch_size)

    return ds

batch_size = exp_config['batch_size']

train_ds_10 = create_train_dataset_10_90(train_data_10_percent, 
                                target_data_10_percent,
                                categorical_features_10_90,
                                batch_size=batch_size,
                                shuffle=True,
                                repeat=True,
                                drop_remainder=True,
                                return_sample_weight=True)

example_data, example_labels, example_sample_weight = next(iter(train_ds_10))

for key in example_data:
    print(f'{key}, shape:{example_data[key].shape}, {example_data[key].dtype}')

print(f'labels shape: {example_labels.shape}')
print(f'sample_weights shape: {example_sample_weight.shape}')

print(f'Columns in train_data_10_percent: {list(train_data_10_percent.columns)}')

def create_preprocessing_model_10(categorical, df):
    ## Create input layers
    preprocess_inputs = {}
    for c in categorical:
        preprocess_inputs[c] = layers.Input(shape=(1,),
                                             dtype=np.float64)
    
    ## Create preprocess layers        
    lookup_layers = {}
    for c in categorical:
        lookup_layers[c] = layers.IntegerLookup(vocabulary=df[c].unique(),
                                                 output_mode='int')
                
    ## Create outputs
    preprocess_outputs = {}
    for c in categorical:
        preprocess_outputs[c] = lookup_layers[c](preprocess_inputs[c])
            
    ## Create model
    preprocessing_model = tf.keras.Model(preprocess_inputs,
                                         preprocess_outputs)
    
    return preprocessing_model, lookup_layers

## Create preprocessing model
preprocessing_model, lookup_layers = create_preprocessing_model_10(
    categorical_features_10_90, train_data)

## Apply the preprocessing model in tf.data.Dataset.map
train_ds_10 = train_ds_10.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)

## Display a preprocessed input sample
example_data = next(train_ds_10.take(1).as_numpy_iterator())[0]
for key in example_data:
    print(f'{key}, shape: {example_data[key].shape}, {example_data[key].dtype}')

test_ds_90 = create_train_dataset_10_90(test_data_90_percent, 
                                test_target_data_90_percent,
                                categorical_features_10_90,
                                batch_size=batch_size,
                                shuffle=True,
                                repeat=False,
                                drop_remainder=True,
                                return_sample_weight=True)

test_ds_90 = test_ds_90.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)

## Model compile
learning_rate = exp_config['learning_rate']
weight_decay = exp_config['weight_decay']

learning_schedule = tf.keras.optimizers.schedules.CosineDecay(
    initial_learning_rate=learning_rate,
    decay_steps=epochs*steps_per_epoch, 
    alpha=0.0)

optimizer = tfa.optimizers.AdamW(
    learning_rate=learning_schedule,
    weight_decay=weight_decay)

loss_fn = keras.losses.BinaryCrossentropy()

## Compile model
model_2.compile(optimizer=optimizer,
                loss=loss_fn,
                metrics=[keras.metrics.BinaryAccuracy()],
                weighted_metrics = [])


## Callbacks
min_lr = 1e-6 # minimum learning rate
max_lr = 1e-1 # maximum learning rate
lr_find_epochs = 1
lr_find_steps = 100
lr_find_batch_size = 512

lr_find = LRFind(min_lr, max_lr, lr_find_steps)

## Finding Learning rate
model_2.fit(train_ds_10,
            steps_per_epoch=lr_find_steps,
            epochs=lr_find_epochs,
            callbacks=[lr_find])

## Evaluate model on test dataset
test_loss, test_accuracy = model_2.evaluate(test_ds_90, batch_size=lr_find_batch_size)

print('Test loss: {:.4f}'.format(test_loss))
print('Test accuracy: {:.4f}%'.format(test_accuracy * 100))

plt.plot(lr_find.lrs, lr_find.losses)
plt.xscale('log')
plt.show()