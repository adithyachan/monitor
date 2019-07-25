#!/usr/bin/env bash

docker-compose -f dockerStuff/docker-compose.yml down
pkill -9 -f services-metrics-proc.py
