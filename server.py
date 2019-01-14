from http.server import BaseHTTPRequestHandler, HTTPServer
import xpathgen as xpath

class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # GET
    def do_GET(self):
        # Send response status code
        self.send_response(200)
        # Send headers
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        message = "Hello world!"
        self.wfile.write(bytes(message, "utf8"))
        return

    def do_POST(self):
        # Send response status code
        self.send_response(200)
        # Send headers
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("Recieved data:", post_data.decode('utf-8'), "\n")
        answer = xpath.exec(post_data.decode('utf-8'))
        # Send message back to client
        message = answer
        # Write content as utf-8 data
        self.wfile.write(bytes(message, "utf8"))
        return

def run():
    print('Starting server...')
    server_address = ('0.0.0.0', 8081)
    httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)
    print('Running server...')
    httpd.serve_forever()

run()
