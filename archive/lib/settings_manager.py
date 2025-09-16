#!/usr/bin/env python3
"""
Settings Manager
Handles persistent storage of controller settings
"""

import json
import os

class SettingsManager:
    """Manage persistent controller settings"""
    
    def __init__(self, settings_file="controller_settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            "controller_ip": "",
            "controller_password": "",
            "auto_connect": False,
            "refresh_interval": 5,
            "zone_names": {}
        }
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to handle new settings
                    merged = self.default_settings.copy()
                    merged.update(settings)
                    return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return self.default_settings.copy()
    
    def save_settings(self, settings):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def update_setting(self, key, value):
        """Update a single setting"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)
    
    def get_setting(self, key, default=None):
        """Get a single setting value"""
        settings = self.load_settings()
        return settings.get(key, default)
