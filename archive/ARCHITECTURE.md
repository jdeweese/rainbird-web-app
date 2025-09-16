# RainBird Web App - Architecture Documentation

## 🏗️ Architecture Overview

### New Architecture (Post-Refactor)
```
Frontend (frontend.html) 
    ↓ HTTP API calls
Backend (rainbird_backend.py)
    ↓ Direct communication
RainBird Controller (192.168.1.113)
```

### Old Architecture (Legacy)
```
Frontend (index.html) 
    ↓ /proxy endpoint
Server (server.py)
    ↓ Encrypted JSON-RPC
RainBird Controller
```

## 🔧 Backend Implementation

### Core Components

#### RainBirdBackend Class
- **Purpose**: Main backend service managing controller communication
- **Features**: 
  - Direct controller connection management
  - Full API endpoint implementation
  - On-demand refresh (queries controller when frontend requests)
  - Enhanced error handling and validation

#### Enhanced Libraries
- **rainbird_controller.py**: Complete RainBird API implementation
- **data_formatter.py**: Comprehensive response parsing
- **rainbird_connection.py**: Low-level controller communication
- **settings_manager.py**: Persistent settings management

### API Endpoints

#### Zone Management
- `GET /api/zones` - Get all available zones with names
- `POST /api/zones/start` - Start specific zone with duration
- `POST /api/zones/stop` - Stop specific zone or all zones
- `POST /api/zones/name` - Update zone name

#### System Status
- `GET /api/status` - Get comprehensive system status
  - Irrigation state (active zone, time remaining)
  - Rain sensor status
  - Model information
  - Timestamp

#### Program Management
- `GET /api/programs` - Get all available programs
- `POST /api/programs/run` - Execute specific program

#### Weather Control
- `POST /api/rain-delay` - Set or clear rain delay

#### Settings
- `GET /api/settings` - Load current settings
- `POST /api/settings` - Save settings with action parameter

## 🖥️ Frontend Implementation

### Modern JavaScript Architecture
- **API Client Class**: Clean abstraction for backend communication
- **Async/Await**: Modern promise-based communication
- **Error Handling**: Comprehensive error management
- **Real-time Updates**: Configurable status refresh

### Key Features
- **Separation of Concerns**: Frontend only handles UI, backend handles controller
- **Real-time Status**: Live updates from controller via backend
- **Enhanced UX**: Better error messages and user feedback
- **Responsive Design**: Mobile-optimized interface

## 🔄 Communication Flow

### Zone Start Example
```
1. User clicks "Start Zone 1"
2. Frontend: POST /api/zones/start {zone_id: 1, duration: 10}
3. Backend: Validates request
4. Backend: Sends command to controller (39010258)
5. Controller: Responds with success (003904)
6. Backend: Returns {success: true, result: {...}}
7. Frontend: Updates UI with success message
8. Frontend: Starts timer and updates zone status
```

### Status Update Flow
```
1. Frontend: Periodic GET /api/status (every 5 seconds)
2. Backend: Queries controller for current state (command 48)
3. Controller: Returns irrigation state (C801 = Zone 1 active)
4. Backend: Parses response and formats data
5. Backend: Returns structured status object
6. Frontend: Updates system status display
```

## 📊 Data Flow

### Controller Response Parsing
```
Raw Controller Data: "C801"
    ↓ data_formatter.py
Parsed Data: {
    active: true,
    zone: 1,
    time_remaining: 0,
    raw_data: "C801"
}
    ↓ Backend API
JSON Response: {
    success: true,
    status: {
        irrigation_state: {...},
        rain_sensor: {...},
        timestamp: 1757990490
    }
}
```

## 🔧 Configuration Management

### Settings Storage
- **Server-side**: `controller_settings.json`
- **Frontend Cache**: `window.currentSettings`
- **Persistence**: All changes saved to server immediately

### Zone Names
- **Storage**: `settings.zone_names` object
- **Format**: `{"1": "Front Yard", "2": "Back Yard"}`
- **Updates**: Real-time via `/api/zones/name` endpoint

## 🚀 Deployment

### Development Server
```bash
python3 rainbird_backend.py
# Serves on http://localhost:8000
# Includes static file serving for frontend.html
```

### Production Considerations
- **HTTPS**: Add SSL/TLS for secure communication
- **Authentication**: Add user authentication if needed
- **Logging**: Enhanced logging for production monitoring
- **Error Handling**: Production-grade error responses

## 🔍 Debugging

### Backend Debugging
- **Console Logs**: All controller communication logged
- **Error Responses**: Detailed error messages in API responses
- **Status Endpoint**: Real-time controller state inspection

### Frontend Debugging
- **Browser Console**: All API calls and responses logged
- **Network Tab**: Inspect HTTP requests/responses
- **Status Updates**: Real-time status monitoring

## 📈 Performance

### Optimizations
- **On-demand Queries**: Backend only queries controller when frontend requests
- **Efficient Parsing**: Optimized data parsing and formatting
- **Connection Reuse**: Single controller connection per backend instance
- **Minimal Polling**: Configurable refresh intervals

### Scalability
- **Stateless API**: Each request is independent
- **Clean Separation**: Frontend and backend can be deployed separately
- **Extensible**: Easy to add new endpoints and features

## 🔒 Security

### Current Implementation
- **Local Network**: Designed for local network use only
- **Controller Authentication**: Uses controller password for all commands
- **Input Validation**: Backend validates all input parameters

### Future Enhancements
- **HTTPS**: Secure communication
- **Rate Limiting**: Prevent API abuse
- **Authentication**: User login system
- **CORS**: Cross-origin request handling
