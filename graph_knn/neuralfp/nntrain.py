import tensorflow as tf
from utils.nn import *
from mol_graph import atom_fdim as adim, bond_fdim as bdim, max_nb, smiles2graph_list
import math, sys, random
from optparse import OptionParser
from collections import deque
        
parser = OptionParser()
parser.add_option("-t", "--train", dest="train_path")
parser.add_option("-v", "--valid", dest="valid_path")
parser.add_option("-m", "--save_dir", dest="save_path")
parser.add_option("-b", "--batch", dest="batch_size", default=20)
parser.add_option("-w", "--hidden", dest="hidden_size", default=145)
parser.add_option("-d", "--depth", dest="depth", default=4)
opts,args = parser.parse_args()

batch_size = int(opts.batch_size)
hidden_size = int(opts.hidden_size)
depth = int(opts.depth)

gpu_options = tf.GPUOptions(allow_growth=True)
session = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))

input_atom = tf.placeholder(tf.float32, [batch_size, None, adim])
input_bond = tf.placeholder(tf.float32, [batch_size, None, bdim])
atom_graph = tf.placeholder(tf.int32, [batch_size, None, max_nb, 2])
bond_graph = tf.placeholder(tf.int32, [batch_size, None, max_nb, 2])
num_nbs = tf.placeholder(tf.int32, [batch_size, None])
node_mask = tf.placeholder(tf.float32, [batch_size, None])
src_holder = [input_atom, input_bond, atom_graph, bond_graph, num_nbs, node_mask]
label = tf.placeholder(tf.float32, [batch_size])
node_mask = tf.expand_dims(node_mask, -1)

with tf.variable_scope("encoder"):
    atom_features = input_atom
    layers = []
    for i in xrange(depth):
        fatom_nei = tf.gather_nd(atom_features, atom_graph)
        fbond_nei = tf.gather_nd(input_bond, bond_graph)
        h_nei_atom = linearND(fatom_nei, hidden_size, "nei_atom_%d" % i, init_bias=None)
        h_nei_bond = linearND(fbond_nei, hidden_size, "nei_bond_%d" % i, init_bias=None)
        h_nei = h_nei_atom + h_nei_bond
        mask_nei = tf.reshape(tf.sequence_mask(tf.reshape(num_nbs, [-1]), max_nb, dtype=tf.float32), [batch_size,-1,max_nb,1])
        f_nei = tf.reduce_sum(h_nei * mask_nei, -2)
        f_self = linearND(atom_features, hidden_size, "self_atom_%d" % i)
        atom_features = batch_normalization_with_mask(f_nei + f_self, node_mask, "batch_norm_%d" % i, training=True)
        atom_features = tf.nn.relu(atom_features) * node_mask
        outputs = tf.nn.softmax(linearND(atom_features, hidden_size, "output_%d" % i))
        layers.append(outputs * node_mask)
    all_outputs = tf.concat(1, layers)
    fp = tf.reduce_sum(all_outputs, 1)

fp = linear(fp, hidden_size, "output")
fp = tf.nn.relu(fp)

score = tf.squeeze(linear(fp, 1, "score"), [1])
loss = tf.nn.l2_loss(score - label) * 2 

lr = tf.placeholder(tf.float32, [])
optimizer = tf.train.AdamOptimizer(learning_rate=lr)
param_norm = tf.global_norm(tf.trainable_variables())
grads_and_vars = optimizer.compute_gradients(loss / batch_size)
grads, var = zip(*grads_and_vars)
grad_norm = tf.global_norm(grads)
backprop = optimizer.apply_gradients(grads_and_vars)

tf.global_variables_initializer().run(session=session)
size_func = lambda v: reduce(lambda x, y: x*y, v.get_shape().as_list())
n = sum(size_func(v) for v in tf.trainable_variables())
print "Model size: %dK" % (n/1000,)

def load_data(path):
    data = []
    with open(path) as f:
        f.readline()
        for line in f:
            r,v = line.strip("\r\n ").split()
            data.append((r,float(v)))
    return data

def evaluate(data):
    sum_err = 0.0
    for it in xrange(0, len(data), batch_size):
        batch = data[it:it+batch_size]
        if len(batch) < batch_size:
            batch.extend(data[0:batch_size - len(batch)])
        src_batch, label_batch = zip(*batch)
        src_tuple = smiles2graph_list(src_batch)
        label_batch = np.array(label_batch)

        feed_map = {x:y for x,y in zip(src_holder, src_tuple)}
        feed_map.update({label:label_batch})
        err = session.run(loss, feed_dict=feed_map)
        sum_err += err
    return math.sqrt(sum_err / len(data))

saver = tf.train.Saver()
train = load_data(opts.train_path)
valid = load_data(opts.valid_path)
random.shuffle(train)
buckets = [deque() for i in xrange(300)]
for i in xrange(len(train)):
    idx = int(train[i][1] / 0.05)
    buckets[idx].append(i)
for i in xrange(299, 0, -1):
    if len(buckets[i]) == 0:
        buckets.pop(i)

sum_err, sum_gnorm = 0.0, 0.0
it = 0
_lr = 0.001
while True:
    it += batch_size
    batch = []
    for i in xrange(batch_size):
        buk = random.choice(buckets)
        idx = buk.popleft()
        batch.append(train[idx])
        buk.append(idx)

    src_batch, label_batch = zip(*batch)
    src_tuple = smiles2graph_list(src_batch)

    feed_map = {x:y for x,y in zip(src_holder, src_tuple)}
    feed_map.update({label:label_batch, lr:_lr})
    _, err, pnorm, gnorm = session.run([backprop, loss, param_norm, grad_norm], feed_dict=feed_map)
    sum_err += err
    sum_gnorm += gnorm

    if it % 200 == 0 and it > 0:
        rmse = math.sqrt(sum_err / 200)
        print ("Training RMSE: %.4f, Param Norm: %.2f, Grad Norm: %.2f" % (rmse, pnorm, sum_gnorm / 200) )
        sys.stdout.flush()
        sum_err, sum_gnorm = 0.0, 0.0
    if it % 100000 == 0 and it > 0:
        saver.save(session, opts.save_path + "/model.ckpt-%d" % it)
        print ("Validation RMSE: %.4f" % evaluate(valid))
        _lr *= 0.9
        print ("Learning Rate: %.6f" % _lr)

saver.save(session, opts.save_path + "/model.final")
