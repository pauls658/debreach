#!/bin/bash

if [[ -z $1 ]]; then
	echo "need stream header file path"
	exit 1
fi

escaped=${1//\//\\\/}
sed -i -e "s/^#include \"streams\/stream_.*$/#include \"$escaped\"/" compressstream.c
pushd ..
make
popd
