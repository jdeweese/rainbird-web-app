# RainBird LNK Controller Web App

A modern web application to control your RainBird LNK WiFi irrigation controller, replicating the functionality of the official RainBird mobile app.

## Features

- **Zone Control**: Start/stop individual irrigation zones with custom duration
- **Program Management**: Run predefined watering programs
- **Real-time Status**: Monitor active zones, remaining time, and rain sensor status
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Clean, intuitive interface with real-time updates

## Architecture

The application is built with a modular architecture:

### Backend (Python)
- **`server.py`** - Main web server and API handler
- **`lib/rainbird_controller.py`** - High-level controller interface
- **`lib/rainbird_connection.py`** - Low-level HTTP/AES communication
- **`lib/rainbird_protocol.py`** - Protocol command definitions
- **`lib/data_formatter.py`** - Response data formatting

### Frontend (JavaScript)
- **`index.html`** - Main web interface
- **`app.js`** - Application logic and UI management
- **`rainbird-api.js`** - Client-side API interface
- **`styles.css`** - Responsive styling

## Setup Instructions

### Prerequisites

- RainBird LNK WiFi controller connected to your network
- Python 3.7+ with `pycryptodome` library
- Web browser with JavaScript enabled
- Controller IP address and password

### Installation

1. **Install dependencies**:
   ```bash
   pip3 install pycryptodome --break-system-packages
   ```

2. **Start the server**:
   ```bash
   ./start-server.sh
   ```

3. **Open your browser** to http://localhost:8000

4. **Connect to your controller**:
   - Enter controller IP address (e.g., 192.168.1.113)
   - Enter controller password
   - Click "Connect"

## Usage

### Connecting to Controller

1. Enter your controller's IP address
2. Enter the controller password
3. Click "Connect"
4. Wait for connection confirmation

### Zone Control

- **Start Zone**: Select duration (1-60 minutes) and click "Start"
- **Stop Zone**: Click "Stop" on any active zone
- **Monitor**: View remaining time for active zones

### System Status

- **Rain Sensor**: Shows if rain sensor is active/inactive
- **Current Zone**: Displays currently running zone
- **Time Remaining**: Shows time left for active zone

## Technical Details

### Protocol Implementation

The app uses the RainBird LNK controller's JSON-RPC API over HTTP:

- **Protocol**: HTTP POST requests to `/stick` endpoint
- **Encryption**: AES encryption with SHA256 key derivation
- **Format**: JSON-RPC 2.0 with encrypted payload

### Supported Commands

- `ModelAndVersionRequest` - Get controller information
- `AvailableStationsRequest` - Retrieve zone configuration
- `CurrentIrrigationStateRequest` - Get current system status
- `ManuallyRunStationRequest` - Start watering a specific zone
- `StopIrrigationRequest` - Stop all active zones
- `CurrentRainSensorStateRequest` - Check rain sensor status

## Development

### File Structure

```
rainbird-web-app/
├── server.py              # Main web server
├── lib/                   # Backend library modules
│   ├── __init__.py
│   ├── rainbird_controller.py    # High-level interface
│   ├── rainbird_connection.py    # HTTP/AES communication
│   ├── rainbird_protocol.py      # Protocol definitions
│   └── data_formatter.py         # Response formatting
├── index.html             # Main HTML interface
├── app.js                 # Frontend application logic
├── rainbird-api.js        # Client-side API
├── styles.css             # Styling
├── start-server.sh        # Server startup script
└── server-config.json     # Server configuration
```

### Server Management

```bash
# Start server
./start-server.sh

# Stop server
pkill -f "python3.*server.py"

# View logs
tail -f server.out
```

## Security Notes

- **Local Network Only**: This app is designed for local network use
- **Password Storage**: Passwords are not stored permanently
- **AES Encryption**: Uses proper AES encryption for secure communication

## License

This project is open source and available under the MIT License.

## Disclaimer

This is an unofficial application. RainBird is a trademark of Rain Bird Corporation. This project is not affiliated with or endorsed by Rain Bird Corporation.
