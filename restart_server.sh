#!/bin/bash
cd "$(dirname "$0")"
./stop_server.sh
sleep 1
./start_server.sh
