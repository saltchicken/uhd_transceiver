import argparse
import socket
import sys
import time
import numpy as np

from loguru import logger

def recv_all(sock, buffer_size):
    data = b''
    while len(data) < buffer_size:
        packet = sock.recv(buffer_size - len(data))
        if not packet:
            # Handle case where connection is closed prematurely
            raise RuntimeError("Socket connection closed prematurely")
        data += packet
    return data

def receive_data(sock):
    """Receive continuous stream of data."""
    total_received = 0
    try:
        while True:
            data_bytes = recv_all(sock, 512000)  # Receive data from the server
            # data_bytes = sock.recv(512000)
            if not data_bytes:
                break
            if len(data_bytes) == 512000:
                data = np.frombuffer(data_bytes, dtype=np.complex64)  # Convert received bytes to numpy array
                total_received += 64000
            else:
                print(f"Goofed {len(data_bytes)}")
            time.sleep(0.010)
    except RuntimeError as e:
        print('Socket closed')
    finally:
        print(f"Total Received: {total_received}")
        sock.close()

def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    #   # Server address and port
    server_address = (args.remote, args.port) if args.remote else ('localhost', args.port)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(server_address)
        receive_data(client_socket)  # Receive data continuously
    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")
    except KeyboardInterrupt:
        print("Client interrupted. Exiting...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
