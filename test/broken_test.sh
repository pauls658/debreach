#!/bin/bash

rm facebook_html_27.gz
../minidebreach -b 638,711,656,811,1067,1251 ./input/facebook_html_27
mv input/facebook_html_27.gz .
gunzip facebook_html_27.gz