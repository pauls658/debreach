#!/bin/bash

/usr/local/php7/7.0.0/bin/phpize
EXTRA_CFLAGS="-O0" LDFLAGS="-O0 -L/usr/local/apache2/modules -l:mod_debreach.so" ./configure --enable-debreach --with-apxs2=/usr/local/apache2/bin/apxs
make clean all
make install
