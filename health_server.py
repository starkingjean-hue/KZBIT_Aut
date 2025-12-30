from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"KZBIT Bot is active!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Health server started on port {port}")
    server.serve_forever()
