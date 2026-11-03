#!/bin/bash
# resume port_all --write after crashes, within ~165 s
start=$(date +%s)
while true; do
  last=$(tail -1 report2.csv | cut -d, -f1)
  next=$((last+1))
  [ $next -ge 164 ] && { echo ALLDONE; break; }
  left=$((165 - ($(date +%s) - start)))
  [ $left -lt 20 ] && { echo "stopped at $next"; break; }
  timeout $left python3 port_all.py $next 200 $((left-10)) --write 2>&1 | tail -1
done
