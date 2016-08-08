from __future__ import print_function
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten, BatchNormalization
from keras.optimizers import SGD
from keras.utils import np_utils
from layers import HaarLayer, ChannelMixerLayer
from keras.layers.core import Lambda
from keras.layers.convolutional import Convolution2D


batch_size = 128
nb_classes = 10
nb_epoch = 100
data_augmentation = True
spatial_conv_first = False

# input image dimensions
img_rows, img_cols = 32, 32
# the CIFAR10 images are RGB
img_channels = 3

# the data, shuffled and split between train and test sets
(X_train, y_train), (X_test, y_test) = cifar10.load_data()
print('X_train shape:', X_train.shape)
print(X_train.shape[0], 'train samples')
print(X_test.shape[0], 'test samples')

# convert class vectors to binary class matrices
Y_train = np_utils.to_categorical(y_train, nb_classes)
Y_test = np_utils.to_categorical(y_test, nb_classes)

model = Sequential()

# BS, 3, 32, 32
if spatial_conv_first == True:
    model.add(Convolution2D(16, 5, 5, border_mode='same', input_shape=(3, 32, 32)))
else:
    model.add(Lambda(lambda x: x.mean(1), output_shape=(32, 32), input_shape=(3, 32, 32)))
    model.add(HaarLayer())

# BS, 32, 32 (or BS, 32, 32, N)
model.add(ChannelMixerLayer(16))
model.add(BatchNormalization())
model.add(Activation('relu'))

# BS, 16, 16, 16
model.add(HaarLayer())
model.add(ChannelMixerLayer(8))
model.add(BatchNormalization())
model.add(Activation('relu'))

# BS, 8, 8, 8, 8
model.add(HaarLayer())
model.add(ChannelMixerLayer(8))
model.add(BatchNormalization())
model.add(Activation('relu'))

# BS, 8, 4, 4, 4, 4 -> 2048
model.add(Flatten())
model.add(Dense(1024))
model.add(Activation('relu'))
model.add(Dropout(0.5))
model.add(Dense(nb_classes))
model.add(Activation('softmax'))

# let's train the model using SGD + momentum (how original).
sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy',
              optimizer=sgd,
              metrics=['accuracy'])

model.summary()

X_train = X_train.astype('float32')
X_test = X_test.astype('float32')
X_train /= 255
X_test /= 255

if not data_augmentation:
    print('Not using data augmentation.')
    bl = model.fit(X_train, Y_train,
              batch_size=batch_size,
              nb_epoch=nb_epoch,
              validation_data=(X_test, Y_test),
              shuffle=True)
else:
    print('Using real-time data augmentation.')

    # this will do preprocessing and realtime data augmentation
    datagen = ImageDataGenerator(
        featurewise_center=False,  # set input mean to 0 over the dataset
        samplewise_center=False,  # set each sample mean to 0
        featurewise_std_normalization=False,  # divide inputs by std of the dataset
        samplewise_std_normalization=False,  # divide each input by its std
        zca_whitening=False,  # apply ZCA whitening
        rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
        width_shift_range=0.1,  # randomly shift images horizontally (fraction of total width)
        height_shift_range=0.1,  # randomly shift images vertically (fraction of total height)
        horizontal_flip=True,  # randomly flip images
        vertical_flip=False)  # randomly flip images

    # compute quantities required for featurewise normalization
    # (std, mean, and principal components if ZCA whitening is applied)
    datagen.fit(X_train)

    # fit the model on the batches generated by datagen.flow()
    bl = model.fit_generator(datagen.flow(X_train, Y_train,
        batch_size=batch_size),
        samples_per_epoch=X_train.shape[0],
        nb_epoch=nb_epoch,
        validation_data=(X_test, Y_test))
                            
