#!/bin/bash

echo "REMEMBER TO EXECUTE WITH \"nice -n -20\""

SETS=1
TIME="date +%s%N"

sites="reddit
facebook
wikipedia
gmail
phpmyadmin
crafted"

for site in $sites; do
	streams="stream_$site\\_*"
	for test_stream in $streams; do
		echo $test_stream
		sleep 1
		res=""
		for ((i=0;i<$SETS;i++)); do
			#echo $line
			s=$( $TIME )
			./compress_stream.sh $test_stream
			res="$res,$[$( $TIME ) - $s]"
		done
		res="$(du -b -d1 input | grep -oE [0-9]*)$res"
		echo $res > $test_stream\\_res
	done
done
