#!/bin/bash

if [[ -z $1 ]]; then
	echo "wtf give arg"
	echo "[lib | validation]"
	exit 1
fi

if [[ $1 == "lib" ]]; then
	cp Makefiles/lib_Makefile Makefile
	make clean
	make
	make install
	apxs -i -a -c mod_debreach.c -I/usr/local/include -L/usr/local/lib -ldz -DDEBREACH
	service apache2 restart
elif [[ $1 == "validation" ]]; then
	cp Makefiles/validation_Makefile Makefile
	make clean
	make
elif [[ $1 == "debug" ]]; then
	cp Makefiles/debug_Makefile Makefile
	make clean
	make
	make install
	apxs -i -a -c mod_debreach.c -g -I/usr/local/include -L/usr/local/lib -ldz -DDEBREACH
	service apache2 stop
else
	echo "bad!"
fi
