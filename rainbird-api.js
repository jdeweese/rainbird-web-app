/**
 * RainBird Controller API Interface - Correct Protocol Implementation v2.1
 * Based on the official RainBird LNK WiFi controller protocol
 */

class RainBirdAPI {
    constructor() {
        this.baseUrl = '';
        this.password = '';
        this.isConnected = false;
    }

    /**
     * Connect to the RainBird controller
     */
    async connect(ipAddress, password) {
        this.baseUrl = `http://${ipAddress}`;
        this.password = password;
        
        try {
            // Test connection with ModelAndVersionRequest
            const response = await this.makeRequest('ModelAndVersionRequest');
            console.log('Connection response:', response);

            if (response && response._type === 'ModelAndVersionResponse') {
                this.isConnected = true;
                return { success: true, message: 'Connected successfully', data: response };
            } else {
                return { success: false, message: 'Invalid response from controller' };
            }
        } catch (error) {
            console.error('Connection failed:', error);
            return { success: false, message: 'Connection failed: ' + error.message };
        }
    }

    /**
     * Make request using RainBird protocol
     */
    async makeRequest(commandName, ...params) {
        const proxyUrl = '/proxy';
        const targetUrl = this.baseUrl + '/stick';
        
        console.log('Making RainBird request:', commandName);
        
        // Get command data
        const commandData = this.getCommand(commandName);
        if (!commandData) {
            throw new Error(`Unknown command: ${commandName}`);
        }

        // Build command hex string
        let command = commandData.command;
        (params || []).forEach(param => { command += param; });

        if (command.length / 2 !== commandData.length) {
            throw new Error("Invalid parameters for command");
        }

        console.log('Sending hex command:', command);

        // Create request body
        const body = {
            "id": 9,
            "jsonrpc": "2.0",
            "method": "tunnelSip",
            "params": {"data": command, "length": commandData.length}
        };

        // For now, send as plain text since we need AES encryption in proxy
        const response = await fetch(proxyUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: targetUrl,
                data: body,
                headers: {
                    "Accept-Language": "en",
                    "Accept-Encoding": "gzip, deflate",
                    "User-Agent": "RainBird/2.0 CFNetwork/811.5.4 Darwin/16.7.0",
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                    "Content-Type": "application/octet-stream"
                },
                encrypt: true,
                password: this.password
            })
        });

        if (!response.ok) {
            throw new Error(`Proxy error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('Proxy response:', result);
        
        if (!result.success) {
            throw new Error(result.error || 'Request failed');
        }
        
        // Process response
        return this.processResponse(result.data, commandData.response);
    }

    /**
     * Process the response from controller
     */
    processResponse(data, expectedResponseCode) {
        try {
            // Handle both object and string responses
            const response = typeof data === 'string' ? JSON.parse(data) : data;
            console.log('Parsed response:', response);
            
            if (response.error) {
                throw new Error(`Controller error ${response.error.code}: ${response.error.message}`);
            }
            
            if (!response.result) {
                throw new Error("Invalid response received");
            }
            
            // Parse the hex result data
            const resultData = response.result.data;
            const resultCode = resultData.substring(0, 2).toUpperCase();
            
            console.log('Result code:', resultCode, 'Expected:', expectedResponseCode, 'Data:', resultData);
            
            // Parse based on response type
            if (resultCode === '82') { // ModelAndVersionResponse
                return {
                    _type: 'ModelAndVersionResponse',
                    modelID: resultData.substring(2, 6),
                    protocolRevisionMajor: parseInt(resultData.substring(6, 8), 16),
                    protocolRevisionMinor: parseInt(resultData.substring(8, 10), 16)
                };
            } else if (resultCode === '01') { // AcknowledgeResponse
                return {
                    _type: 'AcknowledgeResponse',
                    ack: true,
                    commandEcho: resultData.substring(2, 4)
                };
            } else if (resultCode === '00') { // NotAcknowledgeResponse
                return {
                    _type: 'NotAcknowledgeResponse',
                    ack: false,
                    commandEcho: resultData.substring(2, 4),
                    NAKCode: resultData.substring(4, 6)
                };
            } else if (resultCode === 'C8') { // CurrentIrrigationStateResponse
                const irrigationState = parseInt(resultData.substring(2, 4), 16);
                return {
                    _type: 'CurrentIrrigationStateResponse',
                    irrigationState: irrigationState === 1
                };
            } else if (resultCode === 'BE') { // CurrentRainSensorStateResponse
                const sensorState = parseInt(resultData.substring(2, 4), 16);
                return {
                    _type: 'CurrentRainSensorStateResponse',
                    sensorState: sensorState === 1
                };
            } else if (resultCode === '83') { // AvailableStationsResponse
                return {
                    _type: 'AvailableStationsResponse',
                    pageNumber: resultData.substring(2, 4),
                    setStations: resultData.substring(4, 12)
                };
            }
            
            return { _type: 'UnknownResponse', code: resultCode, data: resultData };
            
        } catch (error) {
            console.error('Error processing response:', error);
            throw error;
        }
    }

    /**
     * Get command definition
     */
    getCommand(commandName) {
        const commands = {
            "ModelAndVersionRequest": {"command": "02", "response": "82", "length": 1},
            "CurrentTimeRequest": {"command": "10", "response": "90", "length": 1},
            "CurrentDateRequest": {"command": "12", "response": "92", "length": 1},
            "SerialNumberRequest": {"command": "05", "response": "85", "length": 1},
            "CurrentRainSensorStateRequest": {"command": "3E", "response": "BE", "length": 1},
            "RainDelayGetRequest": {"command": "36", "response": "B6", "length": 1},
            "AvailableStationsRequest": {"command": "03", "response": "83", "length": 2},
            "CurrentIrrigationStateRequest": {"command": "48", "response": "C8", "length": 1},
            "CurrentStationsActiveRequest": {"command": "3F", "response": "BF", "length": 2},
            "StopIrrigationRequest": {"command": "40", "response": "01", "length": 1},
            "ManuallyRunStationRequest": {"command": "39", "response": "01", "length": 4}
        };
        
        return commands[commandName];
    }

    /**
     * Get available zones
     */
    async getZones() {
        try {
            const response = await this.makeRequest('AvailableStationsRequest', '00');
            return response;
        } catch (error) {
            console.error('Error getting zones:', error);
            throw error;
        }
    }

    /**
     * Get current time
     */
    async getCurrentTime() {
        try {
            const response = await this.makeRequest('CurrentTimeRequest');
            return response;
        } catch (error) {
            console.error('Error getting time:', error);
            throw error;
        }
    }

    /**
     * Get programs (placeholder - RainBird doesn't have a direct programs command)
     */
    async getPrograms() {
        try {
            // Return empty array for now since RainBird doesn't have a programs list command
            return [];
        } catch (error) {
            console.error('Error getting programs:', error);
            return [];
        }
    }

    /**
     * Get controller status
     */
    async getControllerStatus() {
        try {
            const response = await this.makeRequest('CurrentIrrigationStateRequest');
            return {
                irrigationActive: response.irrigationState || false,
                activeZone: 0,
                timeRemaining: 0
            };
        } catch (error) {
            console.error('Error getting controller status:', error);
            return {
                irrigationActive: false,
                activeZone: 0,
                timeRemaining: 0
            };
        }
    }

    /**
     * Get rain sensor status (alias for getRainSensorState)
     */
    async getRainSensorStatus() {
        try {
            const response = await this.makeRequest('CurrentRainSensorStateRequest');
            return response.sensorState || false;
        } catch (error) {
            console.error('Error getting rain sensor status:', error);
            return false;
        }
    }

    /**
     * Get rain sensor state
     */
    async getRainSensorState() {
        try {
            const response = await this.makeRequest('CurrentRainSensorStateRequest');
            return response.sensorState || false;
        } catch (error) {
            console.error('Error getting rain sensor state:', error);
            return false;
        }
    }

    /**
     * Start watering a zone
     */
    async startZone(zoneId, duration) {
        try {
            // Convert zone and duration to hex
            const zoneHex = zoneId.toString(16).padStart(4, '0').toUpperCase();
            const durationHex = duration.toString(16).padStart(2, '0').toUpperCase();
            
            const response = await this.makeRequest('ManuallyRunStationRequest', zoneHex, durationHex);
            return response;
        } catch (error) {
            console.error('Error starting zone:', error);
            throw error;
        }
    }

    /**
     * Stop watering a zone
     */
    async stopZone(zoneId) {
        try {
            const response = await this.makeRequest('StopIrrigationRequest');
            return response;
        } catch (error) {
            console.error('Error stopping zone:', error);
            throw error;
        }
    }
}
