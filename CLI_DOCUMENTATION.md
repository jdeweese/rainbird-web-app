# 🌱 Simple RainBird CLI Documentation

## Overview
Simplified command-line interface for RainBird ESP-ME3 controller with both parameter-based and interactive menu operation.

## Features
- ✅ **Simple zone control** - Start zones with duration
- ✅ **Remaining time calculation** - Shows time left for running zones  
- ✅ **Current status display** - See what's running now
- ✅ **Command-line parameters** - Direct operation from command line
- ✅ **Interactive menu** - User-friendly menu system
- ✅ **ESP-ME3 compatible** - Works with basic RainBird controllers

## Installation
```bash
# Ensure PyRainBird is installed
pip3 install pyrainbird --break-system-packages

# Make CLI executable
chmod +x simple_cli.py
```

## Usage Modes

### 1. Interactive Menu Mode
```bash
python3 simple_cli.py
```
- Launches interactive menu
- Prompts for IP and password
- Menu-driven zone control

### 2. Command-Line Parameter Mode
```bash
python3 simple_cli.py --ip IP --password PASS [OPTIONS]
```

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--ip IP` | Controller IP address | `--ip 192.168.1.113` |
| `--password PASS` | Controller password | `--password 1234` |
| `--zone ZONE` | Zone number (1-19) | `--zone 1` |
| `--duration MINS` | Duration in minutes (1-60) | `--duration 10` |
| `--status` | Get current irrigation status | `--status` |
| `--stop` | Stop all irrigation | `--stop` |
| `--help` | Show help information | `--help` |

## Examples

### Connect Only
```bash
python3 simple_cli.py --ip 192.168.1.113 --password 1234
```

### Run Zone 1 for 10 Minutes
```bash
python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10
```

### Get Current Status
```bash
python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status
```

### Stop All Irrigation
```bash
python3 simple_cli.py --ip 192.168.1.113 --password 1234 --stop
```

### Show Help
```bash
python3 simple_cli.py --help
```

## Interactive Menu Options

When running in interactive mode:

1. **Connect to controller** - Enter IP and password
2. **Run zone** - Select zone (1-19) and duration (1-60 minutes)
3. **Get status** - Show current irrigation status with remaining time
4. **Stop all irrigation** - Emergency stop all zones
0. **Exit** - Quit the program

## Status Display

The status command shows:
- **System Status**: Active/Inactive irrigation
- **Current Time**: Current system time
- **Running Zones**: Which zones are active
- **Remaining Time**: Minutes left for each zone (if tracked)

Example output:
```
✅ System Status:
   💧 Irrigation: 🟢 ACTIVE
   🕐 Current Time: 02:30 PM
   🚿 Zone 1: Running (8 minutes remaining)
   🚿 Zone 3: Running (unknown remaining time)
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection failed` | Wrong IP/password | Check controller settings |
| `Zone must be 1-19` | Invalid zone number | Use zones 1-19 only |
| `Duration 1-60 minutes` | Invalid duration | Use 1-60 minutes only |
| `Not connected` | No connection established | Connect first |

## Configuration

### Default Controller Settings
- **IP**: 192.168.1.113 (your controller)
- **Password**: 1234 (your controller)
- **Zones**: 1-19 (ESP-ME3 supports 19 zones)
- **Duration**: 1-60 minutes

### Remaining Time Tracking
- Tracks start time when zones are started via CLI
- Calculates remaining time based on requested duration
- Shows "unknown remaining time" for zones started elsewhere

## Compatibility

### Tested Controllers
- ✅ **ESP-ME3** (Model 9) v2.12
- ✅ **Basic RainBird controllers**

### Requirements
- Python 3.7+
- PyRainBird library
- Network access to controller
- Controller IP and password

## Troubleshooting

### Connection Issues
1. Verify controller IP address
2. Check password is correct
3. Ensure controller is on network
4. Try ping to controller IP

### Zone Control Issues
1. Check zone numbers (1-19 for ESP-ME3)
2. Verify zones are physically connected
3. Check for rain delays or sensor blocks
4. Try manual controller operation

### Status Display Issues
1. Remaining time only shows for CLI-started zones
2. Zones started from other apps show "unknown remaining time"
3. Status updates every time command is run

## Advanced Usage

### Scripting Examples

**Daily watering script:**
```bash
#!/bin/bash
IP="192.168.1.113"
PASS="1234"

# Water front yard zones
python3 simple_cli.py --ip $IP --password $PASS --zone 1 --duration 15
sleep 900  # Wait 15 minutes
python3 simple_cli.py --ip $IP --password $PASS --zone 3 --duration 10
```

**Status monitoring:**
```bash
#!/bin/bash
while true; do
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status
    sleep 60  # Check every minute
done
```

## Support

For issues or questions:
1. Check controller connectivity
2. Verify PyRainBird installation
3. Test with interactive mode first
4. Check CLI documentation examples
