"""
EthioMorph API - Health endpoint
Author: Esubalew Chekol (esubalew.et)
"""
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "ok",
            "framework": "EthioMorph Research Platform",
            "version": "2.0",
            "endpoints": ["/api/analyze", "/api/expand", "/api/templates"]
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
