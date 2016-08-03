"""
Author: angles
Date and time: 27/07/16 - 13:26
"""
import tensorflow as tf
import numpy as np
from tensorflow.contrib.layers.python.layers import utils
from tensorflow.contrib.layers.python.layers import initializers
from tensorflow.python.ops import init_ops
from tensorflow.python.training import moving_averages
from tensorflow.python.framework import ops
from haar import haar_and_1x1_relu

def batch_normalization(inputs, decay, epsilon, is_training):
    inputs_shape = inputs.get_shape()
    dtype = inputs.dtype.base_dtype
    axis = list(range(len(inputs_shape) - 1))
    params_shape = inputs_shape[-1:]
    beta = tf.get_variable('beta', shape=params_shape, dtype=dtype, initializer=init_ops.zeros_initializer)
    gamma = tf.get_variable('gamma', shape=params_shape, dtype=dtype, initializer=init_ops.ones_initializer)
    moving_mean = tf.get_variable('moving_mean', shape=params_shape, dtype=dtype,
                                  initializer=init_ops.zeros_initializer, trainable=False)
    moving_variance = tf.get_variable('moving_variance', shape=params_shape, dtype=dtype,
                                      initializer=init_ops.ones_initializer, trainable=False)
    if is_training:
        mean, variance = tf.nn.moments(inputs, axis, shift=moving_mean)
        update_moving_mean = moving_averages.assign_moving_average(moving_mean, mean, decay)
        update_moving_variance = moving_averages.assign_moving_average(moving_variance, variance, decay)
        with ops.control_dependencies([update_moving_mean, update_moving_variance]):
            outputs = tf.nn.batch_normalization(inputs, mean, variance, beta, gamma, epsilon)
    else:
        outputs = tf.nn.batch_normalization(inputs, moving_mean, moving_variance, beta, gamma, epsilon)
    outputs.set_shape(inputs.get_shape())
    return outputs

def linear(name_scope, inputs, nb_output_channels):
    with tf.variable_scope(name_scope):
        dtype = inputs.dtype.base_dtype
        nb_input_channels = utils.last_dimension(inputs.get_shape(), min_rank=2)
        weights_shape = [nb_input_channels, nb_output_channels]
        weights = tf.get_variable('weights', weights_shape, initializer=initializers.xavier_initializer(), dtype=dtype)
        bias = tf.get_variable('bias', [nb_output_channels], initializer=init_ops.zeros_initializer, dtype=dtype)
        output = tf.nn.bias_add(tf.matmul(inputs, weights), bias)
    return output

def inference(inputs, is_training, batch_norm=False):
    # 128 x 32 x 32 x 3

    inputs_bw = tf.reduce_mean(inputs, reduction_indices=3)

    # 128 x 32 x 32 squeeze?
    
    l1 = haar_and_1x1_relu(inputs_bw, 4, scope_name='haar1',
                           is_training=is_training, batch_norm=batch_norm)
    
    # 128 x 16 x 16 x 4 channels at the end

    l2 = haar_and_1x1_relu(l1, 16, scope_name='haar2',
                           is_training=is_training, batch_norm=batch_norm)

    # 128 x 8 x 8 x 2 x 16
    
    l3 = haar_and_1x1_relu(l2, 8, scope_name='haar3',
                           is_training=is_training, batch_norm=batch_norm)

    # 128 x 4 x 4 x 1 x 8 x 8
    l3_reshaped = tf.reshape(l3, (-1, 4, 4, 8, 8))

    # 128 x 4 x 4 x 8 x 8
    l4 = haar_and_1x1_relu(l3_reshaped, 16, scope_name='haar4',
                           is_training=is_training, batch_norm=batch_norm) 

    # 128 x 2 x 2 x 4 x 4 x 16

    #l5 = haar_and_1x1_relu(l4, 32, scope_name='haar5',
    #                       is_training=is_training, batch_norm=batch_norm)

    # 128 x 1 x 1 x 2 x 2 x 2 x 8 x 32
    
    flattened = tf.reshape(l4, (128, 1024))
    lin1 = linear('lin1', flattened, 1024)
    lin2 = linear('lin2', tf.nn.relu(lin1), 10)
    return lin2


def inference_perceptron(inputs, is_training):
    # 128 x 32 x 32 x 3

    inputs_bw = tf.reduce_mean(inputs, reduction_indices=3)

    dropout_keep_prob = .4 if is_training else 1.
    
    flattened = tf.reshape(inputs_bw, (128, 1024))
    lin1 = linear('lin1', flattened, 1024)
    lin2 = linear('lin2', tf.nn.relu(lin1), 1024)
    lin3 = linear('lin3', tf.nn.relu(lin2), 1024)
    lin4 = linear('lin4', tf.nn.dropout(tf.nn.relu(lin3), keep_prob=dropout_keep_prob), 10)
    return lin4


"""
inputs = tf.placeholder(tf.float32, [128, 32, 32, 3])
outputs = inference(inputs, is_training=True)
"""
