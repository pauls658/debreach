#!/bin/bash

echo "REMEMBER TO EXECUTE WITH \"nice -n -20\""

SETS=60
TIME="date +%s%N"

run_times=""

for ((i=0;i<$SETS;i++)); do
	s=$( $TIME )
	./compress_stream.sh
	run_times+="$[$( $TIME ) - $s],"
done
echo $run_times
