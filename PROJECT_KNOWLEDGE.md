# RainBird Web App - Project Knowledge Base

## Project Overview
A web application to control RainBird LNK WiFi irrigation controllers, replicating the functionality of the official RainBird mobile app.

## Architecture
- **Backend**: Python server (`server.py`) with proxy endpoints
- **Frontend**: HTML/CSS/JavaScript single-page application
- **Communication**: JSON-RPC over HTTP with AES encryption
- **Settings**: Persistent storage in `controller_settings.json`

## Key Files
- `server.py` - Main web server and API handler
- `index.html` - Main web interface with embedded JavaScript
- `lib/settings_manager.py` - Settings persistence
- `lib/rainbird_*.py` - Controller communication libraries
- `styles.css` - Responsive styling
- `controller_settings.json` - Persistent settings storage

## Current Issues & Lessons Learned

### 1. JavaScript Function Definition Problems
**Issue**: Settings button frequently breaks with "function not defined" errors
**Root Cause**: Function definitions get lost during HTML refactoring
**Solution**: Always define global functions at the very top of script tag
**Pattern**: 
```javascript
<script>
// Define ALL global functions FIRST
window.showSettings = function() { ... };
window.closeSettings = function() { ... };
// Then other code...
</script>
```

### 2. Auto-Connect Issues
**Current State**: Auto-connect on page load is not working reliably
**Known Problems**:
- Password masking in server responses (fixed but connection still fails)
- JavaScript execution timing issues
- Event listeners not properly attached
**Debug Steps**: Check browser console for connection attempt logs

### 3. Settings Modal Behavior
**Working**: Settings button opens modal, form fields populate
**Working**: Test Connection button (stays green on success)
**Working**: Close button functionality
**Broken**: Auto-connect after saving settings
**Broken**: Zone/program loading after connection

### 4. Server Endpoint Status
**Working Endpoints**:
- `/api/settings` (load/save) - Returns real passwords now
- `/proxy` - Handles controller communication
**Settings File**: `controller_settings.json` contains real credentials

### 5. Frontend State Management
**Current Pattern**: Global window functions for all interactions
**Problem**: No centralized state management
**Result**: Inconsistent UI updates and connection status

## Development Patterns That Work

### 1. Function Definition
```javascript
// ALWAYS at top of script tag
window.functionName = function() {
    // implementation
};
```

### 2. Server Restart
```bash
./start-server.sh  # Use this script, not manual python commands
```

### 3. Testing Approach
- Use test harness: `http://localhost:8000/test-harness.html`
- Check browser console for errors
- Test individual functions before integration

## Known Working Features
1. Settings modal opens and closes
2. Settings form populates with saved data
3. Test Connection button works and shows status
4. Settings save to server successfully
5. Server serves real passwords (not masked)
6. Disconnect button functionality

## Known Broken Features
1. Auto-connect on page load
2. Zone/program loading after connection
3. Connection status updates
4. Zone control buttons
5. Program control buttons

## Sprint 1 Progress (2025-09-15)

### Completed Work
- **RB-001**: Enhanced auto-connect with comprehensive debugging
- **RB-002**: Improved connection status visual design
- **RB-003**: Better error messaging system
- **Project Setup**: Complete backlog and persona-driven development

### Technical Improvements
- Added extensive console logging for debugging connection flow
- Enhanced CSS with animations and loading indicators  
- Improved error message display with proper styling
- Better validation for settings and connection parameters

### Testing Status
- Auto-connect debugging code deployed
- Visual improvements ready for validation
- Test cases documented in SPRINT1_TESTS.md
- Ready for browser testing and validation

### Next Sprint Planning
- Focus on zone management (RB-004 to RB-008)
- Real-time status updates
- Emergency stop functionality
- Zone naming and customization

## Server Configuration
- **Port**: 8000
- **Settings File**: `controller_settings.json`
- **Debug**: Add console.log/print statements for troubleshooting
- **Restart**: Always restart server after code changes

## Frontend Architecture Issues
**Current**: All JavaScript embedded in HTML
**Problem**: Hard to maintain, easy to break during edits
**Consideration**: Separate JS files might be more stable

## Testing Strategy
1. **Manual Testing**: Always test in browser after changes
2. **Test Harness**: Use `/test-harness.html` for automated testing
3. **Console Logging**: Add debug logs to track execution
4. **Step-by-Step**: Test individual functions before integration

## Connection Flow (Intended)
1. Page loads → Auto-load settings
2. If valid settings → Auto-connect
3. Connection success → Load zones/programs
4. Display controller interface

## Connection Flow (Current Reality)
1. Page loads → Settings load correctly
2. Auto-connect → Not triggering or failing silently
3. Manual connection via settings → Status unclear
4. Zone/program loading → Not happening

## Next Steps for Debugging
1. Add extensive console logging to connection flow
2. Test each step of auto-connect manually
3. Verify JavaScript execution timing
4. Check if event listeners are properly attached
5. Test connection flow step-by-step in browser console

## Important Notes
- **Don't assume server fixes solve frontend issues**
- **Always test the actual user experience**
- **JavaScript function definitions are fragile during HTML edits**
- **Server restart is required after backend changes**
- **Browser refresh may be needed after frontend changes**

## File Modification History
- `index.html`: Frequently modified, prone to JavaScript breakage
- `server.py`: Modified to remove password masking
- Settings persistence: Working correctly
- Connection logic: Needs debugging and testing

## Development Environment
- **Server**: Python 3.13 with pycryptodome
- **Browser**: Modern browser with JavaScript console
- **Testing**: Local development server on localhost:8000
- **Debugging**: Browser console + server logs
