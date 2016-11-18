#!/bin/bash

EXTRA_FLAGS="-DDEBREACH -DPRINT_LITS -DDEBUG_WINDOW -DDEBUG_UNSAFE"

pushd ..
make clean

sed -i "s/^\(CFLAGS=-g -O0  -D_LARGEFILE64_SOURCE=1 -DHAVE_HIDDEN\).*$/\1 $EXTRA_FLAGS/" Makefile
sed -i "s/^\(SFLAGS=-g -O0  -fPIC -D_LARGEFILE64_SOURCE=1 -DHAVE_HIDDEN\).*$/\1 $EXTRA_FLAGS/" Makefile
sed -i "s/^\(static: example\\\$(EXE) minigzip\\\$(EXE)\).*$/\1 minidebreach\\\$(EXE)/" Makefile

make
popd
python validation_test.py
