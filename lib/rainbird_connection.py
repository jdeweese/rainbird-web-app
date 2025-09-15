#!/usr/bin/env python3
"""
RainBird Connection Handler
Handles low-level HTTP communication and AES encryption
"""

import json
import hashlib
import urllib.request
import urllib.error
from Crypto.Cipher import AES
from Crypto import Random

class RainBirdConnection:
    """Handle RainBird controller connections with AES encryption"""
    
    def __init__(self, timeout=10):
        self.timeout = timeout
        
    def make_request(self, controller_ip, password, json_data):
        """Make encrypted request to RainBird controller"""
        try:
            url = f"http://{controller_ip}/stick"
            
            # Encrypt the JSON payload
            payload = json.dumps(json_data)
            encrypted_data = self._aes_encrypt(payload, password)
            
            # Create request with proper headers
            req = urllib.request.Request(url, data=encrypted_data)
            req.add_header('Content-Type', 'application/octet-stream')
            req.add_header('Accept', '*/*')
            req.add_header('User-Agent', 'RainBird/2.0 CFNetwork/811.5.4 Darwin/16.7.0')
            req.add_header('Accept-Language', 'en')
            req.add_header('Accept-Encoding', 'gzip, deflate')
            req.add_header('Connection', 'keep-alive')
            
            # Send request
            response = urllib.request.urlopen(req, timeout=self.timeout)
            response_data = response.read()
            
            # Decrypt response
            decrypted = self._aes_decrypt(response_data, password)
            return {"success": True, "data": json.loads(decrypted)}
            
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return {"success": False, "error": "Device busy - try again"}
            elif e.code == 403:
                return {"success": False, "error": "Authentication failed - check password"}
            else:
                return {"success": False, "error": f"HTTP error {e.code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _aes_encrypt(self, data, password):
        """AES encrypt using RainBird protocol"""
        # Add termination and padding markers
        data_with_padding = data + "\x00\x10"
        
        # Generate key from password using SHA256
        key = hashlib.sha256(password.encode('utf-8')).digest()[:32]
        
        # Generate random IV
        iv = Random.new().read(16)
        
        # Pad data to block size
        padded_data = self._add_pkcs7_padding(data_with_padding).encode('utf-8')
        
        # Generate hash of original data
        data_hash = hashlib.sha256(data.encode('utf-8')).digest()
        
        # Encrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(padded_data)
        
        # Return: hash(32) + iv(16) + encrypted_data
        return data_hash + iv + encrypted_data
    
    def _aes_decrypt(self, encrypted_data, password):
        """AES decrypt using RainBird protocol"""
        # Extract components
        data_hash = encrypted_data[:32]
        iv = encrypted_data[32:48]
        encrypted = encrypted_data[48:]
        
        # Generate key from password
        key = hashlib.sha256(password.encode('utf-8')).digest()[:32]
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted)
        
        # Remove padding and terminators
        result = decrypted.decode('utf-8').rstrip('\x10').rstrip('\x0A').rstrip('\x00').rstrip()
        return result
    
    def _add_pkcs7_padding(self, data):
        """Add PKCS7 padding to reach block size"""
        block_size = 16
        pad_len = block_size - (len(data) % block_size)
        return data + ('\x10' * pad_len)
