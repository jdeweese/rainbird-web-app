# RainBird Web App - Project Backlog

## Epic 1: Core Connection & Status (CRITICAL)
**Priority**: P0 - Blocking all functionality

### User Stories:
- **RB-001**: As a user, I want the app to auto-connect on page load so I don't have to manually connect each time
- **RB-002**: As a user, I want clear connection status so I know if my controller is reachable
- **RB-003**: As a user, I want reliable error messages when connection fails so I can troubleshoot

### Acceptance Criteria:
- Auto-connect works with saved settings
- Connection status updates in real-time
- Error messages are clear and actionable
- Manual reconnection works reliably

---

## Epic 2: Zone Management (HIGH)
**Priority**: P1 - Core irrigation functionality

### User Stories:
- **RB-004**: As a user, I want to start individual zones with custom duration (1-60 minutes)
- **RB-005**: As a user, I want to stop any running zone immediately
- **RB-006**: As a user, I want to see which zones are currently active and time remaining
- **RB-007**: As a user, I want to stop all zones with one emergency stop button
- **RB-008**: As a user, I want to see zone names instead of just numbers

### Acceptance Criteria:
- Zone controls respond within 2 seconds
- Real-time status updates every 5 seconds
- Emergency stop works from any screen
- Zone names are customizable and persistent

---

## Epic 3: Program Management (HIGH)
**Priority**: P1 - Automated irrigation

### User Stories:
- **RB-009**: As a user, I want to run existing programs manually
- **RB-010**: As a user, I want to see program schedules and next run times
- **RB-011**: As a user, I want to enable/disable programs
- **RB-012**: As a user, I want to create simple watering schedules
- **RB-013**: As a user, I want to edit program durations and days

### Acceptance Criteria:
- Programs run correctly with proper zone sequencing
- Schedule display shows next 7 days of watering
- Program changes save to controller permanently
- Program status updates in real-time

---

## Epic 4: System Monitoring (MEDIUM)
**Priority**: P2 - Enhanced functionality

### User Stories:
- **RB-014**: As a user, I want to see rain sensor status to know if watering will be skipped
- **RB-015**: As a user, I want to see system health and controller information
- **RB-016**: As a user, I want to view watering history for the past week
- **RB-017**: As a user, I want to see water usage estimates

### Acceptance Criteria:
- Rain sensor status updates automatically
- System info shows model, firmware, uptime
- History shows dates, zones, and durations
- Usage estimates are reasonably accurate

---

## Epic 5: User Experience (MEDIUM)
**Priority**: P2 - Usability improvements

### User Stories:
- **RB-018**: As a mobile user, I want the app to work well on my phone
- **RB-019**: As a user, I want intuitive navigation and clear visual feedback
- **RB-020**: As a user, I want the app to remember my preferences
- **RB-021**: As a user, I want keyboard shortcuts for common actions

### Acceptance Criteria:
- Mobile responsive design works on phones/tablets
- Loading states and progress indicators
- Settings persist between sessions
- Keyboard navigation works for accessibility

---

## Epic 6: Advanced Features (LOW)
**Priority**: P3 - Nice to have

### User Stories:
- **RB-022**: As a user, I want to set seasonal watering adjustments
- **RB-023**: As a user, I want to integrate with weather services
- **RB-024**: As a user, I want to export watering data
- **RB-025**: As a user, I want multiple controller support

---

## Current Sprint Focus (Sprint 1)
**Goal**: Establish reliable core functionality

### Sprint Backlog:
1. **RB-001**: Fix auto-connect functionality (CRITICAL)
2. **RB-002**: Improve connection status display (HIGH)
3. **RB-003**: Better error messaging (HIGH)
4. **RB-004**: Basic zone start/stop (HIGH)

### Definition of Done:
- Feature works in test harness
- Manual testing passes
- Code committed with proper message
- Documentation updated
