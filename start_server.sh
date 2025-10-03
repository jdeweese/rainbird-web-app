#!/bin/bash
cd "$(dirname "$0")"
python3 server.py &
echo $! > server.pid
echo "Server started with PID $(cat server.pid)"
echo "Access at: http://localhost:8000"
