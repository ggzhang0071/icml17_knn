img="nvcr.io/nvidia/tensorflow:17.10"
TOP=`pwd`/..

nvidia-docker run --privileged=true  -e DISPLAY  --net=host --ipc=host -it --rm  -p 7022:22 -p 5022:5022 \
     -v $TOP:/wrk \
     -w /wrk  \
     $img /bin/bash

