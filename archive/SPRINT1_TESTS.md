# Sprint 1 Test Plan - Core Connection

## Test Case: RB-001 - Auto-Connect Functionality

### Pre-conditions:
- Server running on localhost:8000
- Valid settings in controller_settings.json
- Controller reachable on network

### Test Steps:
1. Open browser to http://localhost:8000
2. Wait 2 seconds for auto-connect
3. Observe connection status

### Expected Results:
- Status changes from "Configure Settings" to "Connecting..." to "Connected"
- Disconnect button appears
- Zones and programs load automatically

### Current Status: ❌ FAILING
**Issue**: Auto-connect not triggering, status stays "Configure Settings"

---

## Test Case: RB-002 - Connection Status Display

### Test Steps:
1. Observe initial status
2. Manually connect via settings
3. Disconnect using disconnect button
4. Try connecting with wrong credentials

### Expected Results:
- Clear status messages at each step
- Visual indicators (colors/icons)
- Status persists during page interactions

### Current Status: ⚠️ PARTIAL
**Issue**: Status updates but not visually prominent

---

## Test Case: RB-003 - Error Messaging

### Test Steps:
1. Try connecting with wrong IP
2. Try connecting with wrong password
3. Try connecting with unreachable controller

### Expected Results:
- Specific error messages for each failure type
- Messages appear prominently
- Messages don't interfere with UI

### Current Status: ❌ FAILING
**Issue**: Generic "Connection Failed" message only
