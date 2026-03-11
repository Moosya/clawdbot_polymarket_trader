#!/usr/bin/env python3
"""
Signals API - Simple HTTP endpoint for dashboard
Returns aggregated signals in JSON format
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import subprocess
import sys

SIGNALS_FILE = '/workspace/signals/aggregated-signals.json'
PORT = 8001

class SignalsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/signals':
            # Run aggregator if file is old or missing
            if not Path(SIGNALS_FILE).exists():
                subprocess.run([sys.executable, '/workspace/scripts/aggregate-signals.py'], 
                             capture_output=True)
            
            # Serve signals
            try:
                with open(SIGNALS_FILE, 'r') as f:
                    data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        elif self.path == '/api/paper-trading':
            # Serve paper trading stats
            try:
                result = subprocess.run(
                    [sys.executable, '/workspace/scripts/paper-trading-tracker.py', 'stats'],
                    capture_output=True,
                    text=True
                )
                
                # Parse stats from output
                with open('/workspace/signals/paper-positions.json', 'r') as f:
                    data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        elif self.path == '/api/refresh':
            # Trigger signal refresh
            try:
                subprocess.run([sys.executable, '/workspace/scripts/aggregate-signals.py'],
                             capture_output=True)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'refreshed'}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), SignalsHandler)
    print(f'🚀 Signals API running on http://localhost:{PORT}')
    print(f'   GET /api/signals - Get all trading signals')
    print(f'   GET /api/paper-trading - Get paper trading stats')
    print(f'   GET /api/refresh - Refresh signals')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Shutting down...')
        server.shutdown()
