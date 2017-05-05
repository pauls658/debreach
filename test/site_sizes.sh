#!/bin/bash

sites="reddit
gmail
facebook
wikipedia
crafted
phpmyadmin"

for site in $sites; do
	size=$( du -c -b input/$site* | tail -1 | grep -oE "[0-9]*" )
	echo "$site $size"
done
