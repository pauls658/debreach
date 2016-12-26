#!/bin/bash

# where the test data is put. the input dir for the compressor
OUTPUT_DIR="input"
# where to look for data
TEST_DATA="test_data"
DOCS_DIR="docs"
# folders in $TEST_DATA to ignore
IGNORE="crafted"

if [[ -z $1 ]]; then
	echo "Need data type"
	echo "Usage: ./make_data.sh <data-type>"
	echo 'Ex: ./make_data.sh "*/*"'
	echo "is all data types"
	echo 'Ex: ./make_data.sh "text/*"'
	echo "is all files with text base type"
	exit 1
fi

doc_type="$1"
rm $OUTPUT_DIR/*

for site_folder in $TEST_DATA/*; do
	site_name=${site_folder##*/}
	if [[ $(echo $IGNORE | grep $site_name) ]]; then
		echo "Skipping $site_name"
		continue
	fi

	echo "Processing $site_name"
	for doc in $site_folder/$DOCS_DIR/$doc_type*; do
		# t is the doc type for this doc
		t=$(echo $doc | grep -o -E "[^/]*/[^/]*$")
		out_file=$(printf "$OUTPUT_DIR/%s_%s" $site_name ${t/\//_})
		cp $doc $out_file
	done
done
