import socket
import threading
import queue
import uuid
import os
import select
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

print("Ship Proxy Client is starting...")

OFFSHORE_HOST = os.getenv("OFFSHORE_HOST", "localhost")
OFFSHORE_PORT = int(os.getenv("OFFSHORE_PORT", 9999))
BUFFER_SIZE = 8192

request_queue = queue.Queue()
response_events = {}
offshore_socket = None
socket_lock = threading.Lock()

def connect_to_offshore():
    global offshore_socket
    while True:
        try:
            print(f"Connecting to offshore proxy at {OFFSHORE_HOST}:{OFFSHORE_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((OFFSHORE_HOST, OFFSHORE_PORT))
            offshore_socket = sock
            print("✅ Successfully connected to offshore proxy.")
            return
        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
            threading.Event().wait(5)
        except Exception as e:
            print(f"Error connecting to offshore proxy: {e}. Retrying in 5 seconds...")
            threading.Event().wait(5)

def tcp_worker():
    connect_to_offshore()
    threading.Thread(target=listen_for_responses, daemon=True).start()
    while True:
        handler, request_id, full_request = request_queue.get()
        print(f"{datetime.now().isoformat()} [{request_id.hex()}] Processing request from queue...")
        try:
            with socket_lock:
                if offshore_socket is None: raise ConnectionError("Offshore socket is not connected.")
                payload = request_id + full_request
                msg_len = len(payload).to_bytes(4, 'big')
                print(f"{datetime.now().isoformat()} [{request_id.hex()}] Sending request to offshore proxy.")
                offshore_socket.sendall(msg_len + payload)
        except (ConnectionError, BrokenPipeError) as e:
            print(f"Connection error: {e}. Re-queueing request and reconnecting.")
            request_queue.put((handler, request_id, full_request))
            connect_to_offshore()
        except Exception as e:
            print(f"Error in TCP worker: {e}")
            handler.send_error(500)
            response_events.pop(request_id, None)

def listen_for_responses():
    global offshore_socket
    while True:
        try:
            if offshore_socket is None:
                threading.Event().wait(1)
                continue

            len_bytes = offshore_socket.recv(4)
            if not len_bytes: raise ConnectionError("Connection closed by offshore proxy.")
            msg_len = int.from_bytes(len_bytes, 'big')

            data = b''
            while len(data) < msg_len:
                chunk = offshore_socket.recv(min(msg_len - len(data), BUFFER_SIZE))
                if not chunk: raise ConnectionError("Connection lost while reading payload.")
                data += chunk

            print(f"{datetime.now().isoformat()} Received framed response from offshore.")

            request_id = data[:16]
            response_data = data[16:]

            if request_id in response_events:
                event, container = response_events[request_id]
                container['data'] = response_data
                event.set()
            else:
                print(f"Warning: Received response for unknown request ID {request_id.hex()}")

        except (ConnectionError, BrokenPipeError, OSError) as e:
            print(f"Response listener connection error: {e}. Worker will reconnect.")
            with socket_lock:
                offshore_socket = None
        except Exception as e:
            print(f"Error in response listener: {e}")

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def handle_standard_request(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b''
        headers_str = "\r\n".join(f"{k}: {v}" for k, v in self.headers.items())
        full_request = (f"{self.command} {self.path} {self.request_version}\r\n{headers_str}\r\n\r\n").encode('utf-8') + body

        request_id = uuid.uuid4().bytes
        event = threading.Event()
        response_container = {}
        response_events[request_id] = (event, response_container)

        request_queue.put((self, request_id, full_request))

        print(f"{datetime.now().isoformat()} [{request_id.hex()}] Handler waiting for response...")
        if event.wait(timeout=60): # Keep the 60s timeout
            response_data = response_container.get('data')
            if response_data: self.wfile.write(response_data)
            else: self.send_error(500, "No response from proxy")
            print(f"{datetime.now().isoformat()} [{request_id.hex()}] Handler finished.")
        else:
            self.send_error(504, "Proxy request timed out")
            print(f"{datetime.now().isoformat()} [{request_id.hex()}] Handler timed out.")

        response_events.pop(request_id, None)

    def do_GET(self): self.handle_standard_request()
    def do_POST(self): self.handle_standard_request()
    def do_PUT(self): self.handle_standard_request()
    def do_DELETE(self): self.handle_standard_request()
    def do_HEAD(self): self.handle_standard_request()
    def do_OPTIONS(self): self.handle_standard_request()
    def handle_one_request(self):
        try: BaseHTTPRequestHandler.handle_one_request(self)
        except (socket.error, ConnectionResetError): pass
    def do_CONNECT(self):
        self.send_error(501, "CONNECT not implemented in this debug version")

class ThreadingHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        thread = threading.Thread(target=self.finish_request, args=(request, client_address))
        thread.daemon = True
        thread.start()

def main():
    threading.Thread(target=tcp_worker, daemon=True).start()
    server_address = ('0.0.0.0', 8080)
    httpd = ThreadingHTTPServer(server_address, ProxyHTTPRequestHandler)
    print(f"🚢 Ship proxy listening on port 8080...")
    httpd.serve_forever()

if __name__ == "__main__":
    main()