# -*- coding: utf-8 -*-
"""Adult_Income_MLP.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10faviiFkJjyb7XF4hBAxyEPJ5Z-OyZAl
"""

!python --version

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

import pandas as pd
import numpy as np

MainDF = pd.read_csv("https://raw.githubusercontent.com/tirthvyas-tk-labs/Housing_dataset/main/adult.csv")

MainDF[MainDF == '?'] = np.nan

for col in ['workclass', 'occupation', 'native.country']:
    MainDF[col].fillna(MainDF[col].mode()[0], inplace=True)

grouped = MainDF.groupby('sex')

source_domain_male_df = grouped.get_group('Male')
target_domain_female_df = grouped.get_group('Female')

from sklearn import preprocessing

categorical = ['workclass', 'education', 'marital.status', 'occupation', 'relationship', 'race', 'sex', 'native.country', 'income']
for feature in categorical:
        le = preprocessing.LabelEncoder()
        source_domain_male_df[feature] = le.fit_transform(source_domain_male_df[feature])

numerical_features = [
    "age",
    "education.num",
    "capital.gain",
    "capital.loss",
    "hours.per.week",
]

categorical_features = ['workclass', 'fnlwgt', 'education',
       'marital.status', 'occupation', 'relationship', 'race', 'sex',
       'native.country','income']

source_domain_male_df_scaled = source_domain_male_df.copy()

from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# create an instance of the StandardScaler
scaler = MinMaxScaler()

# fit the scaler to your data and transform it
scaled_data = scaler.fit_transform(source_domain_male_df_scaled)

# create a pandas dataframe from the scaled data
source_domain_male_df_scaled = pd.DataFrame(scaled_data, columns=source_domain_male_df_scaled.columns)

display(source_domain_male_df_scaled)

source_domain_male_df

# Train valid split
val_size = exp_config['val_size']

valid_data = source_domain_male_df[:val_size]
train_data = source_domain_male_df[val_size:]

valid_label = source_domain_male_df_scaled[:val_size]
train_label = source_domain_male_df_scaled[val_size:]

print("train_data: " ,len(train_data))
print("valid_data: " ,len(valid_data))
print("train_label: " ,len(train_label))
print("valid_label: " ,len(valid_label))

import pandas as pd
import numpy as np
import tensorflow as tf

def create_train_dataset(data_df,
                         target_df,
                         categorical_features,
                         numerical_features,
                         mask_ratio=0.2,
                         mask_token=-100,
                         batch_size=128, 
                         shuffle=True,
                         repeat=False,
                         drop_remainder=False,
                         return_sample_weight=True):
    
    data_values = data_df.values
    target = target_df.values
    
    # Masking categorical features
    categorical_mask = np.random.random_sample(size=data_df[categorical_features].shape)
    categorical_mask = np.where(categorical_mask < mask_ratio, 1, 0)
    categorical_train_data = np.where(categorical_mask == 1, mask_token, data_values[:, :len(categorical_features)])
    
    # Masking numerical features
    numerical_mask = np.random.random_sample(size=data_df[numerical_features].shape)
    numerical_mask = np.where(numerical_mask < mask_ratio, 1, 0)
    numerical_train_data = np.where(numerical_mask == 1, mask_token, data_values[:, len(categorical_features):])
    
    # Combining masked categorical and numerical features
    train_data = np.concatenate((categorical_train_data, numerical_train_data), axis=1)
    
    train_data = train_data.astype(np.float64)
    target = target.astype(np.float64)
    
    data = {}
    for i, cf in enumerate(categorical_features):
        data[cf] = train_data[:, i]
    for i, nf in enumerate(numerical_features):
        data[nf] = train_data[:, i + len(categorical_features)]
        
    if return_sample_weight:
        sample_weight = np.concatenate((categorical_mask, numerical_mask), axis=1).astype(np.float64)
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
                                numerical_features,
                                mask_ratio=mask_ratio,
                                mask_token=mask_token,
                                batch_size=batch_size,
                                shuffle=True,
                                repeat=True,
                                drop_remainder=True,
                                return_sample_weight=True)


valid_ds = create_train_dataset(valid_data,
                                valid_label,
                                categorical_features,
                                numerical_features,
                                mask_ratio=mask_ratio,
                                mask_token=mask_token,
                                batch_size=batch_size,
                                shuffle=False,
                                repeat=False,
                                drop_remainder=True,
                                return_sample_weight=True)


example_data, example_labels, example_sample_weight = next(train_ds.take(1).as_numpy_iterator())

for key in example_data:
    print(f'{key}, shape:{example_data[key].shape}, {example_data[key].dtype}')
    
print(f'labels shape: {example_labels.shape}')
print(f'sample_wegihts shape: {example_sample_weight.shape}')

def create_preprocessing_model(categorical, numerical, df, mask_token=-100):
    ## Create input layers
    preprocess_inputs = {}
    for c in categorical:
        preprocess_inputs[c] = layers.Input(shape=(1,),
                                             dtype=np.float64)

    for n in numerical:
        preprocess_inputs[n] = layers.Input(shape=(1,),
                                             dtype=np.float64)
        

    
    ## Create preprocess layers        
    lookup_layers = {}

    for c in categorical:
        lookup_layers[c] = layers.IntegerLookup(vocabulary=df[c].unique(),
                                            mask_token=mask_token,
                                            output_mode='int')
        
    for n in numerical:
        lookup_layers[n] = layers.IntegerLookup(vocabulary=df[n].unique(),
                                            mask_token=mask_token,
                                            output_mode='int')
        
                
    ## Create outputs
    preprocess_outputs = {}
    for c in categorical:
        preprocess_outputs[c] = lookup_layers[c](preprocess_inputs[c])

    for n in numerical:
        preprocess_outputs[n] = lookup_layers[n](preprocess_inputs[n])
            
    ## Create model
    preprocessing_model = tf.keras.Model(preprocess_inputs,
                                         preprocess_outputs)
    
    return preprocessing_model, lookup_layers

## Create preprocessing model
preprocessing_model, lookup_layers = create_preprocessing_model(
    categorical_features,numerical_features, train_data, mask_token=mask_token)

## Apply the preprocessing model in tf.data.Dataset.map
train_ds = train_ds.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)

valid_ds = valid_ds.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)

## Display a preprocessed input sample
example_data = next(train_ds.take(1).as_numpy_iterator())[0]
for key in example_data:
    print(f'{key}, shape: {example_data[key].shape}, {example_data[key].dtype}')

def TabTransformer4(categorical, numerical, lookup_layers, 
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
    model_inputs.update({key: layers.Input(shape=(1,),
                                           dtype='float64') for key in numerical})
    

    # Encode categorical features
    categorical_features = []
    for key in categorical:
        embedding = layers.Embedding(input_dim=lookup_layers[key].vocabulary_size(),
                                    output_dim=embedding_dim)
        encoded_feature = embedding(model_inputs[key])
        categorical_features.append(encoded_feature)

    # Encode numerical features with MLP
    numerical_features = []
    for key in numerical:
        layer = layers.Dense(units=embedding_dim, 
                            activation=keras.activations.selu)(model_inputs[key])
        layer = layers.Reshape((1, embedding_dim))(layer)
        numerical_features.append(layer)

    # Reshape numerical features to have the same sequence length as categorical features
    for i in range(len(numerical_features)):
        numerical_features[i] = layers.Reshape((1, embedding_dim))(numerical_features[i])

    # Concatenate the list of features
    if len(categorical_features) > 0 and len(numerical_features) > 0:
        features = layers.concatenate(categorical_features + numerical_features, axis=1)
    elif len(categorical_features) > 0:
        features = layers.concatenate(categorical_features, axis=1)
    elif len(numerical_features) > 0:
        features = layers.concatenate(numerical_features, axis=1)
    else:
        raise ValueError("At least one categorical or numerical feature is required.")  

    for block_idx in range(num_transformer_blocks):
        ## Create a multi-head attention layer
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=embedding_dim,
            dropout=tf_dropout_rates[block_idx],
            name=f'multi-head_attention_{block_idx}'
        )(features, features)
        ## Skip connection 1
        x = layers.Add(
            name=f'skip_connection1_{block_idx}'
        )([attention_output, features])
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
        features = layers.LayerNormalization(
            name=f'layer_norm2_{block_idx}', 
            epsilon=1e-6
        )(x)
        
    mlp_layers = []
    mlp_hidden_units = [
        int(factor * features.shape[-1]) for factor in mlp_hidden_units_factors]
    
    for i, units in enumerate(mlp_hidden_units):
        mlp_layers.append(layers.BatchNormalization())
        mlp_layers.append(layers.Dense(units,
                                       activation=keras.activations.selu))
        mlp_layers.append(layers.Dropout(mlp_dropout_rates[i]))
    mlp_layers.append(layers.Dense(1, activation=None))
    model_outputs = keras.Sequential(mlp_layers, name='MLP')(features)
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
training_model4 = TabTransformer4(categorical_features, numerical_features,
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
keras.utils.plot_model(training_model4, show_shapes=True, rankdir="LR")

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

training_model4.compile(optimizer=optimizer,
                       loss=loss_fn,
                       metrics=[keras.metrics.RootMeanSquaredError(),
                                keras.metrics.MeanAbsoluteError()])

training_model4.summary()

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
training_model4.compile(optimizer=optimizer,
                       loss=loss_fn,
                       metrics=[keras.metrics.RootMeanSquaredError(),
                                keras.metrics.MeanAbsoluteError()])

training_model4.fit(train_ds,
                   steps_per_epoch=lr_find_steps,
                   epochs=lr_find_epochs,
                   callbacks=[lr_find])

plt.plot(lr_find.lrs, lr_find.losses)
plt.xscale('log')
plt.show()

def model_training(training_model, preprocessing_model, 
                   data_df, target_df, epochs, 
                   val_size=5000, batch_size=256):
    train_losses = []
    valid_losses = []
    for _ in range(epochs):
        ## Create train and valid datasets
        random_idx = np.random.permutation(np.arange(len(source_domain_male_df)))
        
        valid_data = data_df.iloc[random_idx[:val_size]]
        train_data = data_df.iloc[random_idx[val_size:]]
        
        valid_target = target_df.iloc[random_idx[:val_size]]
        train_target = target_df.iloc[random_idx[val_size:]]
        
        train_ds = create_train_dataset(train_data, 
                                        train_target,
                                        categorical_features,
                                        numerical_features,
                                        mask_ratio=mask_ratio,
                                        mask_token=mask_token,
                                        batch_size=batch_size,
                                        shuffle=False,
                                        repeat=False,
                                        drop_remainder=False,
                                        return_sample_weight=True)
        
        train_ds = train_ds.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                                num_parallel_calls=tf.data.AUTOTUNE)
        
        valid_ds = create_train_dataset(valid_data, 
                                        valid_target,
                                        categorical_features,
                                        numerical_features,
                                        mask_ratio=mask_ratio,
                                        mask_token=mask_token,
                                        batch_size=batch_size,
                                        shuffle=False,
                                        repeat=False,
                                        drop_remainder=False,
                                        return_sample_weight=True)
        
        valid_ds = valid_ds.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                                num_parallel_calls=tf.data.AUTOTUNE)
        
        # Model training
        history = training_model.fit(train_ds,
                                     epochs=1,
                                     shuffle=False,
                                     validation_data=valid_ds,
                                    )
        
        train_losses.append(history.history['loss'])
        valid_losses.append(history.history['val_loss'])
        
        gc.collect()
        
    return train_losses, valid_losses

## Settings for Training
epochs = exp_config['train_epochs']
val_size = exp_config['val_size']
batch_size = exp_config['batch_size']
steps_per_epoch = len(source_domain_male_df)//batch_size 

## Re-construct the model
training_model_config = training_model4.get_config()
training_model = tf.keras.Model.from_config(training_model_config)

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
                                keras.metrics.MeanAbsoluteError()],
                                weighted_metrics = [])

## Model training
train_losses, valid_losses = model_training(training_model, 
                                            preprocessing_model, 
                                            data_df=source_domain_male_df,
                                            target_df=source_domain_male_df_scaled,
                                            epochs=epochs, 
                                            val_size=val_size,
                                            batch_size=batch_size)

## Plot the train and valid losses
plt.figure(figsize=(7, 5))
plt.plot(np.arange(epochs), train_losses, label='Train Loss')
plt.plot(np.arange(epochs), valid_losses, label='Valid Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.show()

# make all layers untrainable by freezing weights (except for last layer)
for l, layer in enumerate(training_model4.layers):
    layer.trainable = False

training_model4.summary()

inputs = training_model4.input

x = training_model4.output
x = keras.layers.Dense(64, activation='relu')(x)
x = keras.layers.Dense(32, activation='relu')(x)
x = keras.layers.Dense(1, activation='sigmoid')(x)

outputs = tf.squeeze(x)

model_2 = keras.models.Model(inputs=inputs, outputs=outputs)

model_2.summary()

target_domain_female_df

categorical = ['workclass', 'education', 'marital.status', 'occupation', 'relationship', 'race', 'sex', 'native.country', 'income']
for feature in categorical:
        le = preprocessing.LabelEncoder()
        target_domain_female_df[feature] = le.fit_transform(target_domain_female_df[feature])

numerical_features = [
    "age",
    "education.num",
    "capital.gain",
    "capital.loss",
    "hours.per.week",
]

categorical_features = ['workclass', 'fnlwgt', 'education',
       'marital.status', 'occupation', 'relationship', 'race', 'sex',
       'native.country','income']

target_domain_female_df_scaled = target_domain_female_df.copy()

from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# create an instance of the StandardScaler
scaler = MinMaxScaler()

# fit the scaler to your data and transform it
scaled_data = scaler.fit_transform(source_domain_male_df_scaled)

# create a pandas dataframe from the scaled data
source_domain_male_df_scaled = pd.DataFrame(scaled_data, columns=source_domain_male_df_scaled.columns)

display(source_domain_male_df_scaled)

from sklearn.model_selection import train_test_split

supervised_90_percent_target_domain_female, supervised_10_percent_target_domain_female = train_test_split(target_domain_female_df, test_size=0.1, random_state=42)

print("Number of samples in 10% portion:", len(supervised_10_percent_target_domain_female))
print("Number of samples in 90% portion:", len(supervised_90_percent_target_domain_female))

target_domain_female_df_scaled_90, target_domain_female_df_scaled_10 = train_test_split(target_domain_female_df_scaled, test_size=0.1, random_state=42)

X = supervised_10_percent_target_domain_female
y = target_domain_female_df_scaled_10['income']

X_test = supervised_90_percent_target_domain_female
y_test = target_domain_female_df_scaled_90['income']

train_data_10_percent = X
target_data_10_percent = y

test_data_90_percent = X_test
test_target_data_90_percent = y_test

print("train_data: " ,len(train_data_10_percent))
print("target_data: " ,len(target_data_10_percent))

print("test_data: " ,len(test_data_90_percent))
print("test_target_data: " ,len(test_target_data_90_percent))

def create_train_dataset_10_90(data_df,
                                target_df,
                                categorical_features,
                                numerical_features,  # add numerical features
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
    for i, cf in enumerate(categorical_features):
        data[cf] = data_values[:, i]
    for i, nf in enumerate(numerical_features):  # add numerical features
        data[nf] = data_values[:, len(categorical_features) + i]

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
                                categorical_features,
                                numerical_features,
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

def create_preprocessing_model_10(categorical, numerical, df):
    ## Create input layers
    preprocess_inputs = {}
    for c in categorical:
        preprocess_inputs[c] = layers.Input(shape=(1,),
                                             dtype=np.float64)

    for n in numerical:
        preprocess_inputs[n] = layers.Input(shape=(1,),
                                             dtype=np.float64)
            
    ## Create preprocess layers        
    lookup_layers = {}
    for c in categorical:
        lookup_layers[c] = layers.IntegerLookup(vocabulary=df[c].unique(),
                                                 output_mode='int')
    for n in numerical:
        lookup_layers[n] = layers.IntegerLookup(vocabulary=df[n].unique(),
                                            output_mode='int')                
    ## Create outputs
    preprocess_outputs = {}
    for c in categorical:
        preprocess_outputs[c] = lookup_layers[c](preprocess_inputs[c])
    for n in numerical:
        preprocess_outputs[n] = lookup_layers[n](preprocess_inputs[n])
                        
    ## Create model
    preprocessing_model = tf.keras.Model(preprocess_inputs,
                                         preprocess_outputs)
    
    return preprocessing_model, lookup_layers

## Create preprocessing model
preprocessing_model, lookup_layers = create_preprocessing_model_10(
    categorical_features, numerical_features, train_data)

## Apply the preprocessing model in tf.data.Dataset.map
train_ds_10 = train_ds_10.map(lambda x, y, sw: (preprocessing_model(x), y, sw),
                        num_parallel_calls=tf.data.AUTOTUNE)

## Display a preprocessed input sample
example_data = next(train_ds_10.take(1).as_numpy_iterator())[0]
for key in example_data:
    print(f'{key}, shape: {example_data[key].shape}, {example_data[key].dtype}')

test_ds_90 = create_train_dataset_10_90(test_data_90_percent, 
                                test_target_data_90_percent,
                                categorical_features,
                                numerical_features,
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
lr_find_steps = 200
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