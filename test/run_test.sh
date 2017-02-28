#!/bin/bash

iters=$(grep -E "#define ROUNDS [0-9]*" timeit.c | grep -o -E "[0-9]*")

for testcase in testcases/*; do
    arg=$(cat $testcase)
	arg=${arg#*\ }
	in_file=${testcase/testcases/input}
	time=$(nice -n 20 ../timeit $arg $in_file)
	# fuck bash
	zero=0
	size=$(stat --printf="%s" $in_file)
	echo "$in_file,$size,$time,$iters"
	if [ $? -ne $zero ]; then
		echo "../timeit $arg $in_file"
		echo "timeit has non-zero return: $?"
		exit 1
	fi
done
