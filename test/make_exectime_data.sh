#!/bin/bash

if [[ -z $1 ]]; then
	echo "Need site name"
	exit 1
fi

if [[ -z $2 ]]; then
	echo "Need stream format"
	exit 1
fi

rm input/*
for har_file in /home/brandon/thesis/test_data/$1/$1*.har; do
	python har2docs.py -a -s $har_file input $1
done

python make_test_cases.py -$2
