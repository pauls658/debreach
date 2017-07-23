#!/bin/bash

if [[ -z $1 ]]; then
	echo "wtf give arg"
	exit 1
fi

if [[ $1 == "lib" ]]; then
	cp Makefiles/lib_Makefile Makefile
	make clean
	make
	make install
	service apache2 restart
elif [[ $1 == "validation" ]]; then
	cp Makefiles/validation_Makefile Makefile
	make clean
	make
else
	echo "bad!"
fi
