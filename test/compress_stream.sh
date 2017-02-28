#!/bin/bash

while read -r line; do
	#printf "%s" $line
	../singlefile $line
done < stream
