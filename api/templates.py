"""
EthioMorph API - Templates endpoint
Author: Esubalew Chekol (esubalew.et)
"""
from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            templates_path = os.path.join(base_dir, 'data', 'templates.json')
            
            with open(templates_path, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            
            self.wfile.write(json.dumps(templates, ensure_ascii=False, indent=2).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())
