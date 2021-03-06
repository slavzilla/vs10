import tensorflow as tf
import numpy as np
import os
import time
from random import shuffle
from tensorflow.keras.layers import Input, Conv1D, Conv1DTranspose, Concatenate, AlphaDropout
from tensorflow.keras.losses import MeanAbsoluteError
from tensorflow.keras.initializers import LecunNormal
from tensorflow.keras.models import Model
from tensorflow.keras.activations import tanh
from tensorflow.keras.optimizers import Nadam
import matplotlib.pyplot as plt

SIGNAL_LENGTH = 442368
dataset_path = "VS10_tf"
BATCH_SIZE = 32
EPOCH_LEN = 300
EPOCH = int(300 / BATCH_SIZE)
BUFFER_SIZE = 64
NUM_EPOCHS = 40

GLOROT_INITIALIZER = 'glorot_normal'

def _parse_function_(example):
    features_description = {"signal": tf.io.FixedLenFeature(SIGNAL_LENGTH, tf.float32), "speed": tf.io.FixedLenFeature(1, tf.float32), "instant": tf.io.FixedLenFeature(1, tf.float32)}

    features_dict = tf.io.parse_single_example(example, features_description)

    return (tf.expand_dims(features_dict["signal"], axis=-1), features_dict["speed"], features_dict["instant"])

def generator(iterator):
  try:
    while True:
      yield next(iterator)
  except (RuntimeError, StopIteration):
    return

def compute_loss(model, input):
  ae, _ = model(input)
  return MeanAbsoluteError()(input, ae)

def train_step(model, input, optimizer):
  with tf.GradientTape() as tape:
    loss = compute_loss(model, input)
    gradients = tape.gradient(loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))
  return loss

def get_autoencoder(ss=[SIGNAL_LENGTH, 1]): 
  
    input=Input(shape=ss)

    conv_0 = Conv1D(filters=8, kernel_size=121, strides=1, padding='same', activation='selu', kernel_initializer=LecunNormal())(input) 

    conv_1 = Conv1D(filters=16, kernel_size=61, strides=16, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_0) 

    conv_2 = Conv1D(filters=32, kernel_size=61, strides=8, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_1) 

    conv_3 = Conv1D(filters=64, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_2)

    conv_4 = Conv1D(filters=128, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_3)

    conv_5 = Conv1D(filters=256, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_4) 

    upsampling_0 = Conv1DTranspose(filters=128, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(conv_5)
    upsampling_0 = Concatenate()([upsampling_0, conv_4])

    upsampling_0 = AlphaDropout(rate=0.4)(upsampling_0)

    upsampling_1 = Conv1DTranspose(filters=64, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(upsampling_0)
    upsampling_1 = Concatenate()([upsampling_1, conv_3])

    upsampling_1 = AlphaDropout(rate=0.4)(upsampling_1)

    upsampling_2 = Conv1DTranspose(filters=32, kernel_size=61, strides=4, padding='same', activation='selu', kernel_initializer=LecunNormal())(upsampling_1)
    upsampling_2 = Concatenate()([upsampling_2, conv_2])

    upsampling_2 = AlphaDropout(rate=0.4)(upsampling_2)

    upsampling_3 = Conv1DTranspose(filters=16, kernel_size=61, strides=8, padding='same', activation='selu', kernel_initializer=LecunNormal())(upsampling_2)
    upsampling_3 = Concatenate()([upsampling_3, conv_1])

    upsampling_4 = Conv1DTranspose(filters=8, kernel_size=61, strides=16, padding='same', activation='selu', kernel_initializer=LecunNormal())(upsampling_3)
    upsampling_4 = Concatenate()([upsampling_4, conv_0])

    output = Conv1D(filters=1, kernel_size=121, strides=1, padding='same', activation=tanh, kernel_initializer=GLOROT_INITIALIZER)(upsampling_4) 

    return  Model(inputs = input, outputs = [output, conv_5])

def train():
    filenames = []
    filenames += [os.path.join(dataset_path, file_name) for file_name in os.listdir(dataset_path) if (file_name.endswith('tfrecords'))]

    train_dataset = list(filter(lambda filename: "train" in filename, filenames))
    validation_dataset = list(filter(lambda filename: "val" in filename, filenames))

    shuffle(filenames)
    dataset = tf.data.TFRecordDataset(train_dataset)
    dataset = dataset.map(_parse_function_)
    dataset = dataset.repeat(count=NUM_EPOCHS)
    dataset = dataset.shuffle(buffer_size=BUFFER_SIZE)
    dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)
    it = iter(dataset)

    autoencoder = get_autoencoder()
    input = Input((SIGNAL_LENGTH, 1))
    ae = autoencoder(input)
    model = Model(inputs=input, outputs=ae)
    optimizer = Nadam(learning_rate=1*1e-4, schedule_decay=1e-5)

    ckpt = tf.train.Checkpoint(model=model, optimizer=optimizer, it=it)
    manager = tf.train.CheckpointManager(ckpt, "vs10_unet_15_may", max_to_keep=100)
    manager.restore_or_initialize()

#    step = 0
#    losses = []
#    for batch in generator(it):
#        batch_start_time = time.time()
#        loss = train_step(model, batch[0], optimizer)
#        losses.append(loss.numpy())
#        step += 1
#        print("loss is: ", losses[-1], "batch number is:", step)
#        if (step % EPOCH == 0):
#            manager.save()
#    np.save("losses.npy", losses)


    #temp code


    it = iter(dataset)

    for batch in generator(it):
        break

    output = model(batch[0])
    result = output[0].numpy()
    input = batch[0].numpy()
    o_c = result[0]
    i_c = input[0]
    plt.rcParams["figure.figsize"] = (20,8)
    plt.plot(i_c[281000:281500], 'r', label = 'original')
    plt.plot(o_c[281000:281500], 'b', label = 'rekonstruisani')
    plt.legend()
    plt.show(block=True)
    plt.savefig('test.pdf')

def main():
    train()

if __name__ == '__main__':
    main()
