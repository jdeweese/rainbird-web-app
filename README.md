# RainBird LNK Controller Web App

A modern web application to control your RainBird LNK WiFi irrigation controller, replicating the functionality of the official RainBird mobile app with enhanced web-based features.

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip3 install pycryptodome --break-system-packages
   ```

2. **Start the server**:
   ```bash
   ./start-server.sh
   ```

3. **Open your browser** to http://localhost:8000

4. **Configure settings**: Click ⚙️ Settings and enter your controller IP and password

## ✨ Key Features

### 🌊 Complete Irrigation Control
- **8-Zone Management**: Individual zone control with customizable names
- **Real-time Status**: Live monitoring of active zones and time remaining
- **Emergency Stop**: Immediate stop all zones functionality
- **Duration Control**: 1-60 minute watering sessions

### 📅 Program Management
- **Program Execution**: Run existing irrigation programs
- **Schedule Editing**: Modify program schedules and timing
- **Custom Names**: Editable program names with persistence
- **Real-time Updates**: Status monitoring with configurable refresh rates

### 🌧️ Weather Integration
- **Rain Sensor**: Real-time rain sensor status monitoring
- **Rain Delay**: Manual rain delay controls (24h, 48h, 72h)
- **Weather-aware**: Skip watering based on conditions

### 🎨 Enhanced User Experience
- **Responsive Design**: Optimized for desktop, tablet, and mobile
- **Grid Layout**: Efficient screen space utilization
- **Inline Editing**: Click-to-edit zone and program names
- **Real-time Feedback**: Live status updates and notifications

## 📋 Current Status

### ✅ Production Ready Features
- Real controller integration (tested with actual hardware)
- Complete zone control and monitoring
- Program execution and basic scheduling
- Weather integration (rain sensor + manual delays)
- Responsive web interface with modern design
- Persistent settings and customization

### 🔧 Advanced Features Available
- Editable zone and program names
- Configurable refresh intervals
- Real-time system status monitoring
- Emergency controls and safety features
- Mobile-optimized interface

## 🏗️ Architecture

- **Backend**: Python server with RainBird LNK protocol integration
- **Frontend**: Modern single-page application with real-time updates
- **Communication**: AES-encrypted JSON-RPC over HTTP
- **Storage**: Persistent settings in JSON with localStorage backup
- **Real-time**: Configurable status updates (1-60 second intervals)

## 🧪 Testing & Validation

- **Real Hardware**: Tested with actual RainBird LNK controller
- **Test Harness**: Automated testing at `/test-harness.html`
- **Manual Testing**: Comprehensive user workflow validation
- **Interface Testing**: Screen utilization and responsiveness verified

## 👥 Development Methodology

This project was developed using a **persona-based approach** with specialized roles:
- **Version Controller**: Git management and release coordination
- **Testor**: Quality assurance and user acceptance testing
- **UX Designer**: Interface design and user experience optimization
- **Business User**: Domain expertise and feature requirements
- **Documentor**: Knowledge management and documentation

## 📖 Documentation

- `PROJECT_KNOWLEDGE.md` - Complete technical knowledge base
- `PERSONAS.md` - Development team persona definitions
- `PROJECT_BACKLOG.md` - Feature development roadmap
- `INTERFACE_TESTS.md` - UI/UX validation results
- `MISSING_FEATURES.md` - Advanced feature gap analysis

## 🔧 Development & Customization

### Settings Configuration
- Controller IP and password
- Auto-connect preferences
- Refresh interval (1-60 seconds)
- Zone names and program names
- Rain delay preferences

### Advanced Configuration
See `PROJECT_KNOWLEDGE.md` for:
- RainBird protocol implementation details
- Controller command reference
- Troubleshooting and debugging
- Development patterns and best practices

## 🌐 Browser Compatibility

- **Chrome/Edge**: Full support with all features
- **Firefox**: Full support with all features  
- **Safari**: Full support with all features
- **Mobile Browsers**: Responsive design optimized for touch

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This is an unofficial application. RainBird is a trademark of Rain Bird Corporation. This project is not affiliated with or endorsed by Rain Bird Corporation.

## 🤝 Contributing

This project uses persona-based development. See `PERSONAS.md` for contribution guidelines and development workflow.
