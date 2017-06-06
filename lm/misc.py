import numpy as np

import theano
import theano.tensor as T

from nn import RecurrentLayer, Layer, sigmoid, linear

def read_corpus(path, eos="</s>"):
    data = [ ]
    with open(path) as fin:
        for line in fin:
            data += line.split() + [ eos ]
    return data

def create_batches(data_text, map_to_ids, batch_size):
    data_ids = map_to_ids(data_text)
    N = len(data_ids)
    L = ((N-1)/batch_size) * batch_size
    x = np.copy(data_ids[:L].reshape(batch_size,-1).T)
    y = np.copy(data_ids[1:L+1].reshape(batch_size,-1).T)
    return x, y


class HighwayLayer(object):

    def __init__(self, n_d):
        self.n_d = n_d
        self.gate = Layer(n_d, n_d, sigmoid)

    def forward(self, x, h):
        t = self.gate.forward(x)
        return h*t + x*(1-t)

    @property
    def params(self):
        return self.gate.params

    @params.setter
    def params(self, param_list):
        self.gate.params = param_list



class KernelNN(object):
    '''
    Recurrent network derived from sequence kernel (i.e. string kernel)

    The variant that works better for WSJ language modeling is implemented here
    using the following hyper-parameter configuration:

        1) each layer has n-gram aggregation of n=1

        2) decay factor lambda is controlled using a neural gate:
                lambda[t] = sigmoid_gate(x[t], h[t-1])
                c[t] = lambda[t]*c[t-1] + (1-lambda[t])*(W*x[t])
    '''
    def __init__(self, n_in, n_out, activation, highway=True):
        self.n_in, self.n_out = n_in, n_out
        self.highway = highway
        self.activation = activation

        self.lambda_gate = RecurrentLayer(n_in, n_out, sigmoid)
        self.input_layer = Layer(n_in, n_out, linear, has_bias=False)
        if highway:
            self.highway_layer = HighwayLayer(n_out)

    def forward(self, x, hc):
        assert x.ndim == 2
        assert hc.ndim == 2
        n_in, n_out = self.n_in, self.n_out
        activation = self.activation
        lambda_gate, input_layer = self.lambda_gate, self.input_layer

        c_tm1, h_tm1 = hc[:,:n_out], hc[:,n_out:]
        forget_t = lambda_gate.forward(x, h_tm1)
        in_t = 1-forget_t
        wx_t = input_layer.forward(x)
        c_t = c_tm1*forget_t + wx_t*in_t
        h_t = activation(c_t)
        if self.highway:
            h_t = self.highway_layer.forward(x, h_t)

        return T.concatenate([c_t, h_t], axis=1)

    def forward_all(self, x, hc0=None, return_c=False):
        assert x.ndim == 3 # size (len, batch, d)
        if hc0 is None:
            hc0 = T.zeros((x.shape[1], self.n_out*2), dtype=theano.config.floatX)

        #wx = self.input_layer.forward(x)
        h, _ = theano.scan(
                fn = self.forward,
                sequences = x,
                outputs_info = [ hc0 ]
            )
        if return_c:
            return h
        else:
            return h[:,:,self.n_out:]

    @property
    def params(self):
        lst = self.input_layer.params + self.lambda_gate.params
        if self.highway:
            lst += self.highway_layer.params
        return lst

    @params.setter
    def params(self, param_list):
        k1 = len(self.input_layer.params)
        k2 = len(self.lambda_gate.params)
        self.input_layer.params = param_list[:k1]
        self.lambda_gate.params = param_list[k1:k1+k2]
        if self.highway:
            self.highway_layer.params = param_list[k1+k2:]





