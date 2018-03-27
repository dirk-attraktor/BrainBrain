#!/bin/bash
i=0

while [ $i -lt 500 ]
do
python3 run-google-testcases.py run random
i=$[$i+1]
done
exit 0
