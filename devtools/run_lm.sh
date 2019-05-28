
TOP=`pwd`/..

cd $TOP/lm

data="lstm-char-cnn/data/ptb"
timestamp=`date +%Y%m%d%H%M%S`
cl=`git rev-parse HEAD|cut -c1-7`

if [ ! -d $data ] ;then
   git clone https://github.com/yoonkim/lstm-char-cnn.git  
   pip install Theano==0.9.0
fi

rm -fr *.log
export PYTHONPATH=$TOP                           # Set python lib path
python main.py \
  --train $data/train.txt           \
  --dev   $data/valid.txt \
  --test  $data/test.txt       \
 -d 355 --lr_decay 0.9 --dropout 0.5 --rnn_dropout 0 |tee lm_355_${cl}_$timestamp.log
# Test ppl of 69.3,  5m parameters
python main.py \
  --train $data/train.txt           \
  --dev   $data/valid.txt \
  --test  $data/test.txt       \
  -d 950 --lr_decay 0.95 --lr_decay_epoch 30    |tee lm_950_${cl}_$timestamp.log
        # Test ppl of 65.5,  20m parameters
python main.py \
  --train $data/train.txt           \
  --dev   $data/valid.txt \
  --test  $data/test.txt       \
  -d 860 --lr_decay 0.98 --depth 4 --max_epoch |tee lm_860_${cl}_$timestamp.log
 200     
