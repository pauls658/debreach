#!/bin/bash

echo "REMEMBER TO EXECUTE WITH \"nice -n -20\""

if [[ -z $1 ]]; then
	echo "Need method: {br, randombr, *}"
	echo "usage: ./exectime_test.sh <method> <iterations>"
	exit 1
fi

if [[ -z $2 ]]; then
	echo "Need number of iterations to run for each executable"
	echo "usage: ./exectime_test.sh <method> <iterations>"
	exit 1
fi

METHOD=$1
SETS=$2

# not currently used in this script
sites="reddit
facebook
wikipedia
gmail
phpmyadmin
crafted"

for test_exec in $( ls test_executables/stream_$METHOD\_* ); do
	res_file=${test_exec//*\//}
	./$test_exec $SETS > results/$res_file
done
