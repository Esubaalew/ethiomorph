"""
EthioMorph API Server - Research-Grade Ge'ez Morphology Platform
================================================================
Serves the web UI and exposes research APIs for morphological analysis.

Author: Esubalew Chekol
Website: esubalew.et
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.stemmer import GeezStemmer
from src.conjugator import EthioMorphGenerator

PORT = 9011
WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')

stemmer = GeezStemmer()
generator = EthioMorphGenerator()


class EthioMorphHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for EthioMorph API and web interface."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)
    
    def send_json(self, data, status=200):
        """Send a JSON response with proper headers."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def decode_param(self, param):
        """Decode URL parameter with proper encoding for Ge'ez characters."""
        try:
            return param.encode('latin-1').decode('utf-8')
        except:
            return param
    
    def do_GET(self):
        """Handle GET requests for API endpoints and static files."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == '/api/analyze':
            word = self.decode_param(query.get('word', [''])[0])
            if word:
                result = stemmer.extract_root(word)
                self.send_json(result)
            else:
                self.send_json({"error": "No word provided"}, 400)
            return

        if path == '/api/expand':
            root = self.decode_param(query.get('root', [''])[0])
            if root:
                result = generator.expand_root(root)
                self.send_json(result)
            else:
                self.send_json({"error": "No root provided"}, 400)
            return
        
        if path == '/api/expand/simple':
            root = self.decode_param(query.get('root', [''])[0])
            if root:
                result = generator.expand_root_simple(root)
                self.send_json(result)
            else:
                self.send_json({"error": "No root provided"}, 400)
            return
        
        if path == '/api/generate':
            root = self.decode_param(query.get('root', [''])[0])
            tense = query.get('tense', ['perfective'])[0]
            subject = query.get('subject', ['3sm'])[0]
            
            if root:
                result = generator.generate_word(root, tense, subject)
                self.send_json(result)
            else:
                self.send_json({"error": "No root provided"}, 400)
            return
        
        if path == '/api/nominals':
            root = self.decode_param(query.get('root', [''])[0])
            if root:
                results = {}
                for key in generator.templates.get('nominals', {}):
                    results[key] = generator.generate_nominal(root, key)
                self.send_json(results)
            else:
                self.send_json({"error": "No root provided"}, 400)
            return

        if path == '/api/stems':
            root = self.decode_param(query.get('root', [''])[0])
            if root:
                result = generator.expand_stems(root)
                self.send_json(result)
            else:
                self.send_json({"error": "No root provided"}, 400)
            return

        if path == '/api/templates':
            self.send_json(generator.templates)
            return
        
        if path == '/api/health':
            self.send_json({
                "status": "ok",
                "framework": "EthioMorph Research Platform",
                "version": "2.0"
            })
            return

        if path == '/' or path == '':
            self.path = '/index.html'
        
        return super().do_GET()


if __name__ == '__main__':
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║       EthioMorph Research Platform v2.0                       ║
║       Ge'ez Morphological Analysis Framework                  ║
╠═══════════════════════════════════════════════════════════════╣
║  Server:  http://localhost:{PORT}                              ║
║  API:     http://localhost:{PORT}/api/analyze?word=...         ║
║           http://localhost:{PORT}/api/expand?root=...          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    with socketserver.TCPServer(("", PORT), EthioMorphHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
