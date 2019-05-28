TOP=`pwd`/..

cd $TOP/sst

data="text_convnet/data"
timestamp=`date +%Y%m%d%H%M%S`
cl=`git rev-parse HEAD|cut -c1-7`


if [ ! -d $data ] ;then
   git clone https://github.com/taolei87/text_convnet.git  
   pip install Theano==0.9.0
fi

rm -fr *.log
python main.py \
  --train $data/stsa.binary.phrases.train           \
  --dev   $data/stsa.binary.dev \
  --test  $data/stsa.binary.test           \
  --hidden_dim  10  \
  --learning_rate    0.05 \
  --activation       relu \
  --batch_size       100 \
  --depth            50 \
  --dropout          0.1 \
  --rnn_dropout      0.1\
  --highway          1\
  --lr_decay         10 \
  --multiplicative   1 \
  --max_epoch        5000  |tee sst_${cl}_$timestamp.log

