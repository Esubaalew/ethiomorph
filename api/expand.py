"""
EthioMorph API - Expand endpoint
Author: Esubalew Chekol (esubalew.et)
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.conjugator import EthioMorphGenerator

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        root = query.get('root', [''])[0]
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if not root:
            self.wfile.write(json.dumps({"error": "Missing 'root' parameter"}).encode())
            return
        
        try:
            generator = EthioMorphGenerator()
            result = generator.expand_root(root)
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())
