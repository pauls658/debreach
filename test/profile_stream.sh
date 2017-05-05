#!/bin/bash

if [[ -z $1 ]]; then
	echo "Need stream executable to profile"
	exit 1
fi

ITERS=10


