#!/usr/bin/env python3
# coding=utf-8

import os
from gen_captcha import gen_captcha_text_and_image
from gen_captcha import number
from gen_captcha import alphabet
from gen_captcha import ALPHABET

import numpy as np
import tensorflow as tf

import time
import logging

text, image = gen_captcha_text_and_image()
print("验证码图像channel:", image.shape)  # (60, 160, 3)
# 图像大小
IMAGE_HEIGHT = 60
IMAGE_WIDTH = 160
MAX_CAPTCHA = len(text)
print("验证码文本最长字符数", MAX_CAPTCHA)  # 验证码最长4字符; 我全部固定为4,可以不固定. 如果验证码长度小于4，用'_'补齐


# 把彩色图像转为灰度图像（色彩对识别验证码没有什么用）
def convert2gray(img):
    if len(img.shape) > 2:
        gray = np.mean(img, -1)
        # 上面的转法较快，正规转法如下
        # r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
        # gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
        return gray
    else:
        return img


"""
cnn在图像大小是2的倍数时性能最高, 如果你用的图像大小不是2的倍数，可以在图像边缘补无用像素。
np.pad(image,((2,3),(2,2)), 'constant', constant_values=(255,))  # 在图像上补2行，下补3行，左补2行，右补2行
"""

char_set = number + alphabet + ALPHABET + ['_']  # 如果验证码长度小于4, '_'用来补齐
CHAR_SET_LEN = len(char_set)


# 文本转向量
def text2vec(text):
    text_len = len(text)
    if text_len > MAX_CAPTCHA:
        raise ValueError('验证码最长4个字符')

    vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)

    def char2pos(c):
        if c == '_':
            k = 62
            return k
        k = ord(c) - 48
        if k > 9:
            k = ord(c) - 55
            if k > 35:
                k = ord(c) - 61
                if k > 61:
                    raise ValueError('No Map')
        return k

    for i, c in enumerate(text):
        idx = i * CHAR_SET_LEN + char2pos(c)
        vector[idx] = 1
    return vector


# 向量转回文本
def vec2text(vec):
    char_pos = vec.nonzero()[0]
    text = []
    for i, c in enumerate(char_pos):
        char_at_pos = i  # c/63
        char_idx = c % CHAR_SET_LEN
        if char_idx < 10:
            char_code = char_idx + ord('0')
        elif char_idx < 36:
            char_code = char_idx - 10 + ord('A')
        elif char_idx < 62:
            char_code = char_idx - 36 + ord('a')
        elif char_idx == 62:
            char_code = ord('_')
        else:
            raise ValueError('error')
        text.append(chr(char_code))
    return "".join(text)


"""
#向量（大小MAX_CAPTCHA*CHAR_SET_LEN）用0,1编码 每63个编码一个字符，这样顺利有，字符也有
vec = text2vec("F5Sd")
text = vec2text(vec)
print(text)  # F5Sd
vec = text2vec("SFd5")
text = vec2text(vec)
print(text)  # SFd5
"""


# 生成一个训练batch
def get_next_batch(batch_size=128):
    batch_x = np.zeros([batch_size, IMAGE_HEIGHT * IMAGE_WIDTH])
    batch_y = np.zeros([batch_size, MAX_CAPTCHA * CHAR_SET_LEN])

    # 有时生成图像大小不是(60, 160, 3)
    def wrap_gen_captcha_text_and_image():
        while True:
            text, image = gen_captcha_text_and_image()
            if image.shape == (60, 160, 3):
                return text, image

    for i in range(batch_size):
        text, image = wrap_gen_captcha_text_and_image()
        image = convert2gray(image)

        # 将图片数组一维化
        # 同时将文本也对应在两个二维组的同一行
        batch_x[i, :] = image.flatten() / 255  # (image.flatten()-128)/128  mean为0
        batch_y[i, :] = text2vec(text)

    return batch_x, batch_y


####################################################################

X = tf.placeholder(tf.float32, [None, IMAGE_HEIGHT * IMAGE_WIDTH], name='p_x')
Y = tf.placeholder(tf.float32, [None, MAX_CAPTCHA * CHAR_SET_LEN], name='p_y')
keep_prob = tf.placeholder(tf.float32, name='keep_prob')  # dropout


# 定义CNN
def crack_captcha_cnn(X, Y, keep_prob, w_alpha=0.01, b_alpha=0.1):
    x = tf.reshape(X, shape=[-1, IMAGE_HEIGHT, IMAGE_WIDTH, 1])

    # w_c1_alpha = np.sqrt(2.0/(IMAGE_HEIGHT*IMAGE_WIDTH)) #
    # w_c2_alpha = np.sqrt(2.0/(3*3*32))
    # w_c3_alpha = np.sqrt(2.0/(3*3*64))
    # w_d1_alpha = np.sqrt(2.0/(8*32*64))
    # out_alpha = np.sqrt(2.0/1024)

    # 3 conv layer
    w_c1 = tf.Variable(w_alpha * tf.random_normal([3, 3, 1, 32]))
    b_c1 = tf.Variable(b_alpha * tf.random_normal([32]))
    conv1 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(x, w_c1, strides=[1, 1, 1, 1], padding='SAME'), b_c1))
    conv1 = tf.nn.max_pool(conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv1 = tf.nn.dropout(conv1, keep_prob)

    w_c2 = tf.Variable(w_alpha * tf.random_normal([3, 3, 32, 64]))
    b_c2 = tf.Variable(b_alpha * tf.random_normal([64]))
    conv2 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(conv1, w_c2, strides=[1, 1, 1, 1], padding='SAME'), b_c2))
    conv2 = tf.nn.max_pool(conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv2 = tf.nn.dropout(conv2, keep_prob)

    w_c3 = tf.Variable(w_alpha * tf.random_normal([3, 3, 64, 64]))
    b_c3 = tf.Variable(b_alpha * tf.random_normal([64]))
    conv3 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(conv2, w_c3, strides=[1, 1, 1, 1], padding='SAME'), b_c3))
    conv3 = tf.nn.max_pool(conv3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv3 = tf.nn.dropout(conv3, keep_prob)

    # Fully connected layer
    w_d = tf.Variable(w_alpha * tf.random_normal([8 * 20 * 64, 1024]))
    b_d = tf.Variable(b_alpha * tf.random_normal([1024]))
    dense = tf.reshape(conv3, [-1, w_d.get_shape().as_list()[0]])
    dense = tf.nn.relu(tf.add(tf.matmul(dense, w_d), b_d))
    dense = tf.nn.dropout(dense, keep_prob)

    w_out = tf.Variable(w_alpha * tf.random_normal([1024, MAX_CAPTCHA * CHAR_SET_LEN]))
    b_out = tf.Variable(b_alpha * tf.random_normal([MAX_CAPTCHA * CHAR_SET_LEN]))
    out = tf.add(tf.matmul(dense, w_out), b_out, name='out_put')
    # out = tf.nn.softmax(out)
    return out


# 训练
def train_crack_captcha_cnn():
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=.8)
    sess_config = tf.ConfigProto(gpu_options=gpu_options)
    with tf.Session(config=sess_config) as sess:
        output = crack_captcha_cnn()
        # loss
        # loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(output, Y))
        loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=output, labels=Y))
        # 最后一层用来分类的softmax和sigmoid有什么不同？
        # optimizer 为了加快训练 learning_rate应该开始大，然后慢慢衰
        optimizer = tf.train.AdamOptimizer(learning_rate=0.001).minimize(loss)

        predict = tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN], name='predictions')
        max_idx_p = tf.argmax(predict, 2)
        max_idx_l = tf.argmax(tf.reshape(Y, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
        correct_pred = tf.equal(max_idx_p, max_idx_l)
        accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

        saver = tf.train.Saver()

        sess.run(tf.global_variables_initializer())

        step = 0
        while step < 2001:
            batch_x, batch_y = get_next_batch(64)
            _, loss_ = sess.run([optimizer, loss], feed_dict={X: batch_x, Y: batch_y, keep_prob: 0.75})
            print(step, loss_)

            # 每100 step计算一次准确率
            if step % 1000 == 0:
                batch_x_test, batch_y_test = get_next_batch(100)
                acc = sess.run(accuracy, feed_dict={X: batch_x_test, Y: batch_y_test, keep_prob: 1.})
                print(step, acc)
                # 如果准确率大于50%,保存模型,完成训练
                base_dir = os.path.abspath(os.path.dirname(__file__))
                model_dir = os.path.join(base_dir, "model/model.ckpt")
                # if acc > 0.2:
                saver.save(sess, model_dir, global_step=step)
                    # break

            step += 1


def crack_captcha(captcha_image):
    with tf.Session() as sess:
        output = crack_captcha_cnn()
        saver = tf.train.Saver(max_to_keep=1)
        # saver.restore(sess, tf.train.latest_checkpoint('./number/'))
        saver.restore(sess, tf.train.latest_checkpoint('/Users/alpha/github/model/'))
        # saver.restore(sess, path)
        predict = tf.argmax(tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
        text_list = sess.run(predict, feed_dict={X: [captcha_image], keep_prob: 1})

        text = text_list[0].tolist()
        vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)
        i = 0
        for n in text:
            vector[i * CHAR_SET_LEN + n] = 1
            i += 1
        return vec2text(vector)


def crack_captcha1(captcha_image, model_path):

    with tf.Session(graph=tf.Graph()) as sess:
        X = tf.placeholder(tf.float32, [None, IMAGE_HEIGHT * IMAGE_WIDTH])
        Y = tf.placeholder(tf.float32, [None, MAX_CAPTCHA * CHAR_SET_LEN])
        keep_prob = tf.placeholder(tf.float32)  # dropout

        output = crack_captcha_cnn(X, Y, keep_prob)
        saver = tf.train.Saver(max_to_keep=1)
        # my_model_path = '/Users/alpha/github/model/'
        ckpt = tf.train.get_checkpoint_state(model_path)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)
        # saver.restore(sess, tf.train.latest_checkpoint('./number/'))
        # saver.restore(sess, tf.train.latest_checkpoint('/Users/alpha/github/model/'))
        # saver.restore(sess, path)
        predict = tf.argmax(tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
        text_list = sess.run(predict, feed_dict={X: [captcha_image], keep_prob: 1})

        text = text_list[0].tolist()
        vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)
        i = 0
        for n in text:
            vector[i * CHAR_SET_LEN + n] = 1
            i += 1
        return vec2text(vector)


def predict(captcha_image):
    from load import load_graph
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen_model_filename", default="results/frozen_model.pb", type=str,
                        help="Frozen model file to import")
    parser.add_argument("--gpu_memory", default=.2, type=float, help="GPU memory per process")
    args = parser.parse_args()
    graph = load_graph('/Users/alpha/github/flask/flasky/app/cnn/model/frozen_model.pb')
    x = graph.get_tensor_by_name('prefix/p_x:0')
    y = graph.get_tensor_by_name('prefix/p_y:0')
    keep_prob = graph.get_tensor_by_name('prefix/keep_prob:0')
    print(x, y, keep_prob)
    print('Starting Session, setting the GPU memory usage to %f' % args.gpu_memory)
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=args.gpu_memory)
    sess_config = tf.ConfigProto(gpu_options=gpu_options)
    persistent_sess = tf.Session(graph=graph, config=sess_config)
    out_put = graph.get_tensor_by_name("prefix/out_put:0")
    predict = tf.argmax(tf.reshape(out_put, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
    text_list = persistent_sess.run(predict, feed_dict={x: [captcha_image], keep_prob: 1})
    text = text_list[0].tolist()
    vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)
    i = 0
    for n in text:
        vector[i * CHAR_SET_LEN + n] = 1
        i += 1
    return vec2text(vector)



if __name__ == '__main__':
    # text, image = gen_captcha_text_and_image()
    # image = convert2gray(image)  # 生成一张新图
    # image = image.flatten() / 255  # 将图片一维化
    # print(type(image), image)
    # predict_text = crack_captcha(image)  # 导入模型识别
    # print("正确: {}  预测: {}".format(text, predict_text))
    from PIL import Image
#
    captcha_path = '/Users/alpha/github/Flask/flasky/app/static/captcha.jpg'
    image = Image.open(captcha_path)
    image = np.array(image)
    image = convert2gray(image)  # 生成一张新图
    image = image.flatten() / 255  # 将图片一维化
    model_path = '/Users/alpha/github/model/'
    predict_text = crack_captcha1(image, model_path)  # 导入模型识别
    print("第一次预测: {}".format(predict_text))
# #
#
    predict_text = crack_captcha1(image)  # 导入模型识别
    print("第二次预测: {}".format(predict_text))

    predict_text = crack_captcha1(image)  # 导入模型识别
    print("第三次预测: {}".format(predict_text))
#     captcha_path = '/Users/alpha/github/Flask/flasky/app/static/captcha.jpg'
#     image = Image.open(captcha_path)
#     image = np.array(image)
#     image = convert2gray(image)  # 生成一张新图
#     image = image.flatten() / 255  # 将图片一维化
#     predict_text = crack_captcha(image)  # 导入模型识别
#     print("预测: {}".format(predict_text))
# train_crack_captcha_cnn()

# if __name__ == '__main__':
#     # get_next_batch(64)
#     t1 = time.time()
#     train_crack_captcha_cnn()
#     t2 = time.time()
#     logging.warning('finished time {}'.format(t2 - t1))
