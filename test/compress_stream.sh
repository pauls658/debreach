#!/bin/bash

while read -r line; do
	../singlefile $line
done < $1
