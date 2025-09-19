import socket
import threading
from datetime import datetime

print("Offshore Proxy Server is starting...")

BUFFER_SIZE = 8192

def get_host_port_from_request(request_data):
    try:
        headers = request_data.split(b'\r\n')
        host_header = next(h for h in headers if h.lower().startswith(b'host:')).split(b': ')[1]
        host = host_header.decode()
        port = 80
        if b':' in host_header:
            host, port_str = host.rsplit(b':', 1)
            host = host.decode()
            port = int(port_str)
        return host, port
    except Exception:
        return None, None

def handle_request(ship_socket, request_id, request_data):
    try:
        method = request_data.split(b' ', 1)[0]

        if method == b'CONNECT':
            target_line = request_data.split(b'\r\n')[0]
            target_host, target_port = target_line.split(b' ')[1].split(b':')
            target_port = int(target_port)

            with socket.create_connection((target_host, target_port)) as target_socket:
                response = b'HTTP/1.1 200 Connection established\r\n\r\n'
                response_len = (16 + len(response)).to_bytes(4, 'big')
                ship_socket.sendall(response_len + request_id + response)
                # Tunneling logic would go here
        else:
            host, port = get_host_port_from_request(request_data)
            if not host: raise ValueError("Could not parse host from request")

            print(f"{datetime.now().isoformat()} [{request_id.hex()}] Connecting to target {host}:{port}")
            with socket.create_connection((host, port)) as target_socket:
                print(f"{datetime.now().isoformat()} [{request_id.hex()}] Forwarding request to target")
                target_socket.sendall(request_data)

                response_data = b''
                print(f"{datetime.now().isoformat()} [{request_id.hex()}] Receiving response from target")
                while True:
                    chunk = target_socket.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    response_data += chunk
                print(f"{datetime.now().isoformat()} [{request_id.hex()}] Finished receiving response of {len(response_data)} bytes")

        response_len = (16 + len(response_data)).to_bytes(4, 'big')
        ship_socket.sendall(response_len + request_id + response_data)
        print(f"{datetime.now().isoformat()} [{request_id.hex()}] Sent response back to ship.")

    except Exception as e:
        print(f"Error handling request {request_id.hex()}: {e}")
        error_response = b'HTTP/1.1 500 Internal Server Error\r\n\r\n'
        response_len = (16 + len(error_response)).to_bytes(4, 'big')
        ship_socket.sendall(response_len + request_id + error_response)

def handle_ship_connection(conn):
    print(f"{datetime.now().isoformat()} Established persistent connection with {conn.getpeername()}")
    try:
        while True:
            len_bytes = conn.recv(4)
            if not len_bytes: break
            msg_len = int.from_bytes(len_bytes, 'big')

            data = b''
            while len(data) < msg_len:
                chunk = conn.recv(min(msg_len - len(data), BUFFER_SIZE))
                if not chunk: raise ConnectionError("Connection lost")
                data += chunk

            request_id = data[:16]
            request_data = data[16:]
            print(f"{datetime.now().isoformat()} [{request_id.hex()}] Received framed request from ship.")

            threading.Thread(target=handle_request, args=(conn, request_id, request_data)).start()

    except ConnectionResetError:
        print("Connection with ship proxy was reset.")
    finally:
        conn.close()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 9999))
    server_socket.listen(1)
    print(f"{datetime.now().isoformat()} Offshore proxy listening on port 9999...")
    while True:
        conn, addr = server_socket.accept()
        handle_ship_connection(conn)

if __name__ == "__main__":
    main()