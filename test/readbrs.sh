#!/bin/bash

RAW_NUMS=$( grep -o -E "##### \( [0-9]* - [0-9]* \) #####" /tmp/debreach_validation/tainted_data | grep -o -E "[0-9][0-9]*" | tr '\n' ',')

echo "[${RAW_NUMS:0:${#RAW_NUMS}-1}]"
