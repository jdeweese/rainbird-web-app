#!/bin/bash

# Kill any existing server processes
pkill -f "python3.*server.py" 2>/dev/null

# Start the server
cd "$(dirname "$0")"
nohup python3 server.py > server.out 2>&1 &

# Wait a moment for startup
sleep 2

# Check if server started successfully
if curl -s -I http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ Server started successfully on http://localhost:8000"
else
    echo "❌ Server failed to start. Check server.out for errors."
    exit 1
fi
