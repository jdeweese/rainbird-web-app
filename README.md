# RainBird LNK Controller Web App

A modern web application to control your RainBird LNK WiFi irrigation controller, replicating the functionality of the official RainBird mobile app.

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

## 📋 Current Status

### ✅ Working Features
- Settings modal with form validation
- Test Connection functionality
- Settings persistence to JSON file
- Server proxy for controller communication
- Responsive web interface

### ❌ Known Issues
- **Auto-connect on page load not working**
- **Zone/program loading after connection broken**
- **Connection status updates inconsistent**
- **JavaScript function definitions fragile during refactoring**

## 🏗️ Architecture

- **Backend**: Python server with JSON-RPC proxy
- **Frontend**: Single-page HTML application with embedded JavaScript
- **Communication**: AES-encrypted HTTP requests to RainBird controller
- **Settings**: Persistent storage in `controller_settings.json`

## 🧪 Testing

- **Test Harness**: http://localhost:8000/test-harness.html
- **Manual Testing**: Use browser console for debugging
- **Quick Test**: http://localhost:8000/quick-test.html

## 👥 Development Team

This project uses a persona-based development approach:
- **Version Controller**: Git management and version control
- **Testor**: Quality assurance and user testing
- **UX Designer**: Interface design and user experience
- **Business User**: Domain expertise and requirements
- **Documentor**: Documentation and knowledge management

## 📖 Documentation

- `PROJECT_KNOWLEDGE.md` - Technical knowledge base and lessons learned
- `PERSONAS.md` - Development team persona definitions
- `README.md` - This file with project overview

## 🔧 Development

See `PROJECT_KNOWLEDGE.md` for detailed technical information, known issues, and development patterns.

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This is an unofficial application. RainBird is a trademark of Rain Bird Corporation. This project is not affiliated with or endorsed by Rain Bird Corporation.
