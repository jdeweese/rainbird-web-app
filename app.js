/**
 * RainBird Web App Main Application - v4.0 with Settings & Programs
 */

class RainBirdApp {
    constructor() {
        this.api = new RainBirdAPI();
        this.zones = [];
        this.programs = [];
        this.settings = {};
        this.statusUpdateInterval = null;
        this.selectedZones = new Set();
        this.controllerInfo = null;
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('DOM loaded, initializing RainBird app...');
        await this.loadSettings();
        this.initializeEventListeners();
        
        // Auto-connect if settings are configured
        if (this.settings.controller_ip && this.settings.controller_password) {
            setTimeout(() => this.attemptConnection(), 1000);
        } else {
            this.updateConnectionStatus('disconnected', 'Configure Settings');
        }
        
        console.log('RainBird app initialized:', this);
    }

    /**
     * Load settings from server
     */
    async loadSettings() {
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'load' })
            });
            
            const result = await response.json();
            if (result.success) {
                this.settings = result.settings;
                this.updateSettingsUI();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    /**
     * Save settings to server
     */
    async saveSettings() {
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'save', settings: this.settings })
            });
            
            const result = await response.json();
            return result.success;
        } catch (error) {
            console.error('Failed to save settings:', error);
            return false;
        }
    }

    /**
     * Update settings UI with current values
     */
    updateSettingsUI() {
        document.getElementById('settingsIp').value = this.settings.controller_ip || '';
        document.getElementById('settingsPassword').value = this.settings.controller_password === '****' ? '' : this.settings.controller_password || '';
        document.getElementById('autoConnect').checked = this.settings.auto_connect || false;
        document.getElementById('refreshInterval').value = this.settings.refresh_interval || 5;
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        console.log('Initializing event listeners...');
        
        // Settings button is now handled via inline onclick in HTML
        
        const closeSettings = document.getElementById('closeSettings');
        const saveSettings = document.getElementById('saveSettings');
        const testConnection = document.getElementById('testConnection');
        
        if (closeSettings) {
            closeSettings.addEventListener('click', () => this.hideSettings());
        }
        
        if (saveSettings) {
            saveSettings.addEventListener('click', () => this.handleSaveSettings());
        }
        
        if (testConnection) {
            testConnection.addEventListener('click', () => this.handleTestConnection());
        }
        
        // Connection controls
        const disconnectBtn = document.getElementById('disconnectBtn');
        
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.handleDisconnection());
        }

        // Program controls
        const refreshPrograms = document.getElementById('refreshPrograms');
        const editPrograms = document.getElementById('editPrograms');
        
        if (refreshPrograms) {
            refreshPrograms.addEventListener('click', () => this.loadPrograms());
        }
        
        if (editPrograms) {
            editPrograms.addEventListener('click', () => this.editPrograms());
        }

        console.log('Event listeners initialized');
    }

    /**
     * Show settings modal
     */
    showSettings() {
        console.log('Showing settings modal');
        this.updateSettingsUI();
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'flex';
            console.log('Settings modal displayed');
        } else {
            console.error('Settings modal not found');
        }
    }

    /**
     * Hide settings modal
     */
    hideSettings() {
        document.getElementById('settingsModal').style.display = 'none';
    }

    /**
     * Handle save settings
     */
    async handleSaveSettings() {
        const ip = document.getElementById('settingsIp').value.trim();
        const password = document.getElementById('settingsPassword').value;
        const autoConnect = document.getElementById('autoConnect').checked;
        const refreshInterval = parseInt(document.getElementById('refreshInterval').value);

        if (!ip) {
            alert('Please enter a controller IP address');
            return;
        }

        this.settings = {
            ...this.settings,
            controller_ip: ip,
            controller_password: password || this.settings.controller_password,
            auto_connect: autoConnect,
            refresh_interval: refreshInterval
        };

        const success = await this.saveSettings();
        if (success) {
            this.hideSettings();
            this.showMessage('Settings saved successfully', 'success');
            
            // Auto-connect after saving settings
            setTimeout(() => this.attemptConnection(), 500);
        } else {
            this.showMessage('Failed to save settings', 'error');
        }
    }

    /**
     * Test connection with current settings
     */
    async handleTestConnection() {
        const ip = document.getElementById('settingsIp').value.trim();
        const password = document.getElementById('settingsPassword').value || this.settings.controller_password;

        if (!ip || !password) {
            alert('Please enter both IP address and password');
            return;
        }

        try {
            const result = await this.api.connect(ip, password);
            if (result.success) {
                this.showMessage('Connection test successful!', 'success');
            } else {
                this.showMessage(`Connection test failed: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Connection test failed: ${error.message}`, 'error');
        }
    }

    /**
     * Attempt connection with current settings
     */
    async attemptConnection() {
        if (!this.settings.controller_ip || !this.settings.controller_password) {
            this.updateConnectionStatus('disconnected', 'Configure Settings');
            return;
        }

        try {
            this.updateConnectionStatus('connecting', 'Connecting...');
            
            const result = await this.api.connect(this.settings.controller_ip, this.settings.controller_password);
            
            if (result.success) {
                this.updateConnectionStatus('connected', 'Connected');
                document.getElementById('disconnectBtn').style.display = 'inline-block';
                
                await this.loadControllerData();
                this.startStatusUpdates();
                
                this.showMessage('Connected successfully!', 'success');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Connection failed:', error);
            this.updateConnectionStatus('disconnected', 'Connection Failed - Check Settings');
            this.showMessage(`Connection failed: ${error.message}`, 'error');
        }
    }

    /**
     * Handle connection/disconnection
     */
    async handleConnection() {
        return this.attemptConnection();
    }

    /**
     * Handle disconnection
     */
    handleDisconnection() {
        this.api.disconnect();
        this.updateConnectionStatus('disconnected', 'Disconnected');
        
        document.getElementById('disconnectBtn').style.display = 'none';
        
        this.stopStatusUpdates();
        this.clearZones();
        this.clearPrograms();
        
        this.showMessage('Disconnected', 'info');
    }

    /**
     * Load controller data (zones and programs)
     */
    async loadControllerData() {
        try {
            await Promise.all([
                this.loadZones(),
                this.loadPrograms()
            ]);
        } catch (error) {
            console.error('Failed to load controller data:', error);
        }
    }

    /**
     * Load programs from controller
     */
    async loadPrograms() {
        try {
            console.log('Loading programs...');
            const programInfo = await this.api.makeRequest('getProgramInfo');
            console.log('Program info:', programInfo);
            
            this.displayPrograms(programInfo);
        } catch (error) {
            console.error('Failed to load programs:', error);
            this.displayProgramsError(error.message);
        }
    }

    /**
     * Display programs in UI
     */
    displayPrograms(programData) {
        const programsList = document.getElementById('programsList');
        
        if (!programData || !programData.numPrograms) {
            programsList.innerHTML = '<div class="no-programs">No programs configured</div>';
            return;
        }

        let html = '';
        for (let i = 1; i <= programData.numPrograms; i++) {
            html += `
                <div class="program-item">
                    <h4>Program ${i}</h4>
                    <div class="program-details">
                        Status: ${programData.programOptOutMask && programData.programOptOutMask[i-1] === '1' ? 'Disabled' : 'Enabled'}
                    </div>
                    <div class="program-actions">
                        <button class="btn btn-success" onclick="app.runProgram(${i})">Run</button>
                        <button class="btn btn-secondary" onclick="app.editProgram(${i})">Edit</button>
                    </div>
                </div>
            `;
        }
        
        programsList.innerHTML = html;
    }

    /**
     * Display programs error
     */
    displayProgramsError(error) {
        const programsList = document.getElementById('programsList');
        programsList.innerHTML = `<div class="error-message">Failed to load programs: ${error}</div>`;
    }

    /**
     * Clear programs display
     */
    clearPrograms() {
        document.getElementById('programsList').innerHTML = '<div class="loading-message">Connect to controller to view programs</div>';
    }

    /**
     * Run a program
     */
    async runProgram(programId) {
        try {
            // Note: Program running may need different API call
            this.showMessage(`Running Program ${programId}...`, 'info');
            // Implementation depends on available API
        } catch (error) {
            this.showMessage(`Failed to run program: ${error.message}`, 'error');
        }
    }

    /**
     * Edit programs (placeholder)
     */
    editPrograms() {
        this.showMessage('Program editing not yet implemented', 'info');
    }

    /**
     * Show message to user
     */
    showMessage(message, type = 'info') {
        // Create or update message element
        let messageEl = document.getElementById('messageDisplay');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.id = 'messageDisplay';
            messageEl.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 4px;
                z-index: 1001;
                max-width: 300px;
            `;
            document.body.appendChild(messageEl);
        }

        const colors = {
            success: '#d4edda',
            error: '#f8d7da',
            warning: '#fff3cd',
            info: '#d1ecf1'
        };

        messageEl.textContent = message;
        messageEl.style.backgroundColor = colors[type] || colors.info;
        messageEl.style.display = 'block';

        setTimeout(() => {
            messageEl.style.display = 'none';
        }, 3000);
    }
        const password = document.getElementById('password').value.trim();

        if (this.api.isConnected) {
            // Disconnect
            this.disconnect();
            return;
        }

        if (!ipAddress || !password) {
            this.showError('Please enter both IP address and password');
            return;
        }

        try {
            connectBtn.textContent = 'Connecting...';
            connectBtn.disabled = true;

            console.log('Connect button clicked');
            const result = await this.api.connect(ipAddress, password);

            if (result.success) {
                this.controllerInfo = result.data;
                this.updateConnectionStatus(true);
                this.showSuccess(`Connected to RainBird controller (Model ${result.data.modelID})`);
                
                // Show control panel and load data
                document.getElementById('controlPanel').style.display = 'block';
                await this.loadControllerData();
                this.startStatusUpdates();
                
                // Update connect button to disconnect
                connectBtn.textContent = 'Disconnect';
                connectBtn.className = 'btn btn-danger';
                connectBtn.disabled = false;
            } else {
                this.showError(result.message || 'Connection failed');
                connectBtn.textContent = 'Connect';
                connectBtn.disabled = false;
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.showError('Connection failed: ' + error.message);
            connectBtn.textContent = 'Connect';
            connectBtn.disabled = false;
        }
    }

    /**
     * Disconnect from controller
     */
    disconnect() {
        this.api.isConnected = false;
        this.stopStatusUpdates();
        this.updateConnectionStatus(false);
        
        // Clear queue
        if (this.queueCheckInterval) {
            clearInterval(this.queueCheckInterval);
            this.queueCheckInterval = null;
        }
        this.queuedZones = null;
        
        // Hide control panel
        document.getElementById('controlPanel').style.display = 'none';
        
        // Reset connect button
        const connectBtn = document.getElementById('connectBtn');
        connectBtn.textContent = 'Connect';
        connectBtn.className = 'btn btn-primary';
        connectBtn.disabled = false;
        
        // Clear data
        this.zones = [];
        this.selectedZones.clear();
        this.controllerInfo = null;
    }

    /**
     * Update connection status display
     */
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'connection-status connected';
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'connection-status disconnected';
        }
    }

    /**
     * Load controller data (zones, programs, etc.)
     */
    async loadControllerData() {
        try {
            console.log('Loading controller data...');
            
            // Load zones
            const zonesResponse = await this.api.getZones();
            console.log('Zones response:', zonesResponse);
            
            if (zonesResponse && zonesResponse._type === 'AvailableStationsResponse') {
                // Parse the station data to determine available zones
                const stationData = zonesResponse.setStations;
                console.log('Station data:', stationData);
                
                // Convert hex to binary to find available zones
                const zones = [];
                const hexBytes = stationData.match(/.{2}/g) || [];
                
                let zoneNumber = 1;
                hexBytes.forEach((hexByte, byteIndex) => {
                    const byte = parseInt(hexByte, 16);
                    for (let bit = 0; bit < 8; bit++) {
                        if (byte & (1 << bit)) {
                            zones.push({
                                id: zoneNumber,
                                name: `Zone ${zoneNumber}`,
                                active: false,
                                remainingTime: 0,
                                duration: 10 // Default 10 minutes
                            });
                        }
                        zoneNumber++;
                        if (zoneNumber > 32) break; // Support up to 32 zones
                    }
                });
                
                this.zones = zones;
                console.log('Parsed zones:', this.zones);
            } else {
                // Fallback: create default zones
                console.log('Using fallback zones');
                this.zones = Array.from({length: 4}, (_, i) => ({
                    id: i + 1,
                    name: `Zone ${i + 1}`,
                    active: false,
                    remainingTime: 0,
                    duration: 10
                }));
            }

            this.renderZones();
            this.updateZoneCount();

            // Load programs (empty for RainBird)
            this.programs = [];
            this.renderPrograms();

            // Update status and controller info
            await this.updateStatus();
            this.updateControllerInfo();
            
            console.log('Controller data loaded successfully');
        } catch (error) {
            console.error('Failed to load controller data:', error);
            
            // Fallback zones on error
            this.zones = Array.from({length: 4}, (_, i) => ({
                id: i + 1,
                name: `Zone ${i + 1}`,
                active: false,
                remainingTime: 0,
                duration: 10
            }));
            this.renderZones();
            this.updateZoneCount();
        }
    }

    /**
     * Render zones with modern UI
     */
    renderZones() {
        const zonesGrid = document.getElementById('zonesGrid');
        zonesGrid.innerHTML = '';

        this.zones.forEach(zone => {
            const isQueued = this.queuedZones && this.queuedZones.some(q => q.id === zone.id);
            const queuePosition = isQueued ? this.queuedZones.findIndex(q => q.id === zone.id) + 1 : 0;
            
            const zoneCard = document.createElement('div');
            zoneCard.className = `zone-card ${zone.active ? 'active' : ''} ${this.selectedZones.has(zone.id) ? 'selected' : ''} ${isQueued ? 'queued' : ''}`;
            zoneCard.innerHTML = `
                <div class="zone-header">
                    <div class="zone-name">${zone.name}</div>
                    <div class="zone-status ${zone.active ? 'active' : isQueued ? 'queued' : 'inactive'}">
                        ${zone.active ? 'Active' : isQueued ? `Queued #${queuePosition}` : 'Inactive'}
                    </div>
                </div>
                <div class="zone-controls">
                    <input type="checkbox" class="zone-checkbox" ${this.selectedZones.has(zone.id) ? 'checked' : ''} 
                           onchange="app.toggleZoneSelection(${zone.id})" ${zone.active || isQueued ? 'disabled' : ''}>
                    <input type="number" class="zone-time-input" value="${zone.duration}" min="1" max="60" 
                           onchange="app.updateZoneDuration(${zone.id}, this.value)" ${zone.active || isQueued ? 'disabled' : ''}>
                    <span style="font-size: 0.75rem; color: var(--gray-500);">min</span>
                    <button class="btn zone-btn ${zone.active ? 'btn-danger' : 'btn-success'}" 
                            onclick="app.${zone.active ? 'stopZone' : 'startZone'}(${zone.id})" ${isQueued ? 'disabled' : ''}>
                        ${zone.active ? 'Stop' : isQueued ? 'Queued' : 'Start'}
                    </button>
                </div>
                ${zone.active ? `<div class="remaining-time">⏱️ ${this.formatTime(zone.remainingTime)} remaining</div>` : ''}
                ${isQueued ? `<div class="remaining-time">📋 Position ${queuePosition} in queue</div>` : ''}
            `;
            zonesGrid.appendChild(zoneCard);
        });
    }

    /**
     * Update zone count display
     */
    updateZoneCount() {
        const zoneCountElement = document.getElementById('zoneCount');
        if (zoneCountElement) {
            zoneCountElement.textContent = `${this.zones.length} zones`;
        }
    }

    /**
     * Toggle zone selection for bulk operations
     */
    toggleZoneSelection(zoneId) {
        if (this.selectedZones.has(zoneId)) {
            this.selectedZones.delete(zoneId);
        } else {
            this.selectedZones.add(zoneId);
        }
        this.renderZones();
    }

    /**
     * Select all zones
     */
    selectAllZones() {
        const allSelected = this.selectedZones.size === this.zones.length;
        if (allSelected) {
            this.selectedZones.clear();
        } else {
            this.zones.forEach(zone => this.selectedZones.add(zone.id));
        }
        this.renderZones();
        
        // Update button text
        const selectAllBtn = document.getElementById('selectAllBtn');
        selectAllBtn.textContent = allSelected ? 'Select All' : 'Deselect All';
    }

    /**
     * Start selected zones with bulk time (sequential operation)
     */
    async startSelectedZones() {
        if (this.selectedZones.size === 0) {
            this.showError('Please select zones to start');
            return;
        }

        const bulkTime = parseInt(document.getElementById('bulkTime').value) || 10;
        const selectedZoneIds = Array.from(this.selectedZones).sort((a, b) => a - b);
        
        try {
            // RainBird controllers can only run one zone at a time
            // So we'll start the first zone and queue the others
            const firstZoneId = selectedZoneIds[0];
            await this.startZone(firstZoneId, bulkTime);
            
            if (selectedZoneIds.length > 1) {
                this.showSuccess(`Started Zone ${firstZoneId} for ${bulkTime} minutes. Other zones will start automatically when this one finishes.`);
                
                // Queue the remaining zones
                this.queueZones(selectedZoneIds.slice(1), bulkTime);
            } else {
                this.showSuccess(`Started Zone ${firstZoneId} for ${bulkTime} minutes.`);
            }
            
            this.selectedZones.clear();
            this.renderZones();
        } catch (error) {
            this.showError('Failed to start zones: ' + error.message);
        }
    }

    /**
     * Queue zones to start sequentially
     */
    queueZones(zoneIds, duration) {
        // Store queued zones for display
        this.queuedZones = zoneIds.map(id => ({ id, duration }));
        
        // Check every second if we need to start the next zone
        if (!this.queueCheckInterval) {
            this.queueCheckInterval = setInterval(() => {
                const activeZone = this.zones.find(zone => zone.active);
                
                // If no zone is active and we have queued zones, start the next one
                if (!activeZone && this.queuedZones && this.queuedZones.length > 0) {
                    const nextZone = this.queuedZones.shift();
                    this.startZone(nextZone.id, nextZone.duration);
                    
                    if (this.queuedZones.length === 0) {
                        // No more zones in queue, stop checking
                        clearInterval(this.queueCheckInterval);
                        this.queueCheckInterval = null;
                        this.queuedZones = null;
                    }
                }
            }, 1000);
        }
    }

    /**
     * Update zone duration
     */
    updateZoneDuration(zoneId, duration) {
        const zone = this.zones.find(z => z.id === zoneId);
        if (zone) {
            zone.duration = parseInt(duration) || 10;
        }
    }

    /**
     * Start a specific zone
     */
    async startZone(zoneId, duration = null) {
        try {
            const zone = this.zones.find(z => z.id === zoneId);
            if (!zone) return;

            const runTime = duration || zone.duration;
            await this.api.startZone(zoneId, runTime);
            
            zone.active = true;
            zone.remainingTime = runTime * 60; // Convert to seconds
            this.renderZones();
        } catch (error) {
            this.showError(`Failed to start Zone ${zoneId}: ${error.message}`);
        }
    }

    /**
     * Stop a specific zone
     */
    async stopZone(zoneId) {
        try {
            await this.api.stopZone(zoneId);
            
            const zone = this.zones.find(z => z.id === zoneId);
            if (zone) {
                zone.active = false;
                zone.remainingTime = 0;
            }
            this.renderZones();
        } catch (error) {
            this.showError(`Failed to stop Zone ${zoneId}: ${error.message}`);
        }
    }

    /**
     * Stop all zones
     */
    async stopAllZones() {
        try {
            await this.api.stopIrrigation();
            
            this.zones.forEach(zone => {
                zone.active = false;
                zone.remainingTime = 0;
            });
            this.renderZones();
        } catch (error) {
            this.showError('Failed to stop all zones: ' + error.message);
        }
    }

    /**
     * Render programs section
     */
    renderPrograms() {
        // Programs section already has static content explaining RainBird limitation
    }

    /**
     * Update system status display with modern styling
     */
    async updateStatus() {
        try {
            // Get controller status
            const status = await this.api.getControllerStatus();
            console.log('Controller status:', status);
            
            // Get rain sensor status
            const rainSensorActive = await this.api.getRainSensorStatus();
            console.log('Rain sensor status:', rainSensorActive);
            
            // Update rain sensor card
            const rainSensorCard = document.getElementById('rainSensorCard');
            const rainSensorElement = document.getElementById('rainSensor');
            if (rainSensorElement && rainSensorCard) {
                rainSensorElement.textContent = rainSensorActive ? 'Active' : 'Inactive';
                rainSensorCard.className = `status-card ${rainSensorActive ? 'warning' : 'inactive'}`;
            }
            
            // Find currently active zone
            const activeZone = this.zones.find(zone => zone.active);
            const currentZoneElement = document.getElementById('currentZone');
            const currentZoneCard = document.getElementById('currentZoneCard');
            if (currentZoneElement && currentZoneCard) {
                currentZoneElement.textContent = activeZone ? `${activeZone.name}` : 'None';
                currentZoneCard.className = `status-card ${activeZone ? 'active' : 'inactive'}`;
            }
            
            const timeRemainingElement = document.getElementById('timeRemaining');
            const timeRemainingCard = document.getElementById('timeRemainingCard');
            if (timeRemainingElement && timeRemainingCard) {
                timeRemainingElement.textContent = activeZone ? this.formatTime(activeZone.remainingTime) : '--:--';
                timeRemainingCard.className = `status-card ${activeZone ? 'active' : 'inactive'}`;
            }
                
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    }

    /**
     * Update controller info display
     */
    updateControllerInfo() {
        const controllerModelElement = document.getElementById('controllerModel');
        if (controllerModelElement && this.controllerInfo) {
            controllerModelElement.textContent = `Model ${this.controllerInfo.modelID}`;
        }
    }

    /**
     * Start status updates with reduced frequency
     */
    startStatusUpdates() {
        this.statusUpdateInterval = setInterval(async () => {
            try {
                await this.updateStatus();
                
                // Update remaining times for active zones
                this.zones.forEach(zone => {
                    if (zone.active && zone.remainingTime > 0) {
                        zone.remainingTime--;
                        if (zone.remainingTime <= 0) {
                            zone.active = false;
                        }
                    }
                });
                
                this.renderZones();
            } catch (error) {
                console.error('Status update failed:', error);
            }
        }, 10000); // Update every 10 seconds
    }

    /**
     * Stop status updates
     */
    stopStatusUpdates() {
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
            this.statusUpdateInterval = null;
        }
    }

    /**
     * Format time in MM:SS format
     */
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    /**
     * Show error message with toast notification
     */
    showError(message) {
        this.showToast('Error', message, 'error');
    }

    /**
     * Show success message with toast notification
     */
    showSuccess(message) {
        this.showToast('Success', message, 'success');
    }

    /**
     * Show toast notification
     */
    showToast(title, message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">${title}</div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
            </div>
            <div class="toast-message">${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Show toast with animation
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }

    /**
     * Scan for controllers on the network
     */
    async scanForControllers() {
        const scanBtn = document.getElementById('scanBtn');
        const ipDropdown = document.getElementById('ipDropdown');
        const ipInput = document.getElementById('ipAddress');
        
        try {
            scanBtn.textContent = 'Scanning...';
            scanBtn.disabled = true;
            
            this.showToast('Scanning', 'Scanning network for RainBird controllers...', 'info');
            
            // Get the current network range (assume 192.168.1.x)
            const networkBase = '192.168.1.';
            const foundControllers = [];
            
            // Test common IP ranges in parallel (batches of 10 to avoid overwhelming)
            const promises = [];
            for (let i = 1; i <= 254; i++) {
                const ip = networkBase + i;
                promises.push(this.testControllerIP(ip));
                
                // Process in batches of 20
                if (promises.length >= 20 || i === 254) {
                    const results = await Promise.allSettled(promises);
                    results.forEach((result, index) => {
                        if (result.status === 'fulfilled' && result.value) {
                            foundControllers.push(result.value);
                        }
                    });
                    promises.length = 0; // Clear array
                    
                    // Update progress
                    scanBtn.textContent = `Scanning... ${i}/254`;
                }
            }
            
            if (foundControllers.length > 0) {
                // Populate dropdown with found controllers
                ipDropdown.innerHTML = '<option value="">Select a controller...</option>';
                foundControllers.forEach(controller => {
                    const option = document.createElement('option');
                    option.value = controller.ip;
                    option.textContent = `${controller.ip} (Model ${controller.model})`;
                    ipDropdown.appendChild(option);
                });
                
                // Show dropdown, hide input
                ipInput.style.display = 'none';
                ipDropdown.style.display = 'block';
                document.getElementById('manualBtn').style.display = 'inline-block';
                
                // Handle dropdown selection
                ipDropdown.addEventListener('change', (e) => {
                    if (e.target.value) {
                        ipInput.value = e.target.value;
                    }
                });
                
                this.showSuccess(`Found ${foundControllers.length} RainBird controller(s)`);
            } else {
                this.showError('No RainBird controllers found on network. Please enter IP manually.');
            }
            
        } catch (error) {
            console.error('Scan error:', error);
            this.showError('Network scan failed: ' + error.message);
        } finally {
            scanBtn.textContent = 'Scan Network';
            scanBtn.disabled = false;
        }
    }

    /**
     * Test if an IP address has a RainBird controller
     */
    async testControllerIP(ip) {
        try {
            const response = await fetch('http://localhost:8001/proxy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: `http://${ip}/stick`,
                    data: {
                        id: 9,
                        jsonrpc: '2.0',
                        method: 'tunnelSip',
                        params: { data: '02', length: 1 }
                    },
                    headers: {
                        'User-Agent': 'RainBird/2.0 CFNetwork/811.5.4 Darwin/16.7.0',
                        'Content-Type': 'application/octet-stream'
                    },
                    encrypt: true,
                    password: '1234' // Try default password
                })
            });

            const result = await response.json();
            
            if (result.success && result.data) {
                const data = JSON.parse(result.data);
                if (data.result && data.result.data && data.result.data.startsWith('82')) {
                    // Extract model ID from response
                    const modelID = data.result.data.substring(2, 6);
                    return { ip, model: modelID };
                }
            }
            return null;
        } catch (error) {
            return null; // IP not reachable or not a RainBird controller
        }
    }

    /**
     * Show manual entry (switch from dropdown back to input)
     */
    showManualEntry() {
        const ipInput = document.getElementById('ipAddress');
        const dropdown = document.getElementById('ipDropdown');
        const manualBtn = document.getElementById('manualBtn');
        const scanBtn = document.getElementById('scanBtn');

        ipInput.style.display = 'block';
        dropdown.style.display = 'none';
        manualBtn.style.display = 'none';
        scanBtn.style.display = 'inline-block';
    }
}

// Global function for inline onclick
window.showSettings = function() {
    console.log('Settings button clicked via global function');
    if (window.app) {
        window.app.showSettings();
    }
};

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', async () => {
    app = new RainBirdApp();
    window.app = app; // Make app globally accessible
    await app.init();
});

// Make app globally available for onclick handlers
window.app = app;
