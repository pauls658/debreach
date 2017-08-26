#!/bin/bash

/usr/local/php7/7.0.0/bin/phpize
LDFLAGS="-L/usr/local/apache2/modules -l:mod_debreach.so" ./configure --enable-debreach --with-apxs2=/usr/local/apache2/bin/apxs
make clean all
make install
