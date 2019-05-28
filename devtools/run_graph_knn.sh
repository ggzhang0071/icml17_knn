TOP=`pwd`/..

cd $TOP/graph_knn/

timestamp=`date +%Y%m%d%H%M%S`
cl=`git rev-parse HEAD|cut -c1-7`


export PYTHONPATH=$TOP/graph_knn
for i in loopybp neuralfp wlkernel;
do
   cd $i
   rm -fr *.log
   #Training:
   python nntrain.py --train data/tain.txt --valid $valid.txt --save_dir ./model |tee graph_knn_${i}_train_${cl}_$timestamp.log
   #Testing:
   python nntest.py --test data/test.txt --model ./model  |tee graph_knn_${i}_test_${cl}_$timestamp.log
   cd ..
done
