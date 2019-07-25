#!/usr/bin/env bash

docker-compose -f dockerStuff/docker-compose.yml up -d > monitorScripts/logs/log.txt
pip3 install influxdb
python3 monitorScripts/services-metrics-proc.py&
