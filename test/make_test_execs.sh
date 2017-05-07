#!/bin/bash

if [[ -z $1 ]]; then
	echo "need method: {br, randombr, *}"
	exit 1
fi
METHOD=$1

echo "Changing Makefile to exectime_Makefile"
cp ../Makefiles/exectime_Makefile ..

for header_file in $( ls streams/stream_$METHOD\_*.h ); do
	./compile_stream.sh $header_file
	exec_name=${header_file/.h/}
	exec_name=${exec_name/streams/test_executables}
	echo $exec_name
	mv ../compressstream $exec_name
done
