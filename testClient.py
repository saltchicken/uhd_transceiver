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

class UHD_Client():
    def __init__(self, sock):
        self.sock = sock
        self.segment = b''
        
    def receive_data(self):
        """Receive continuous stream of data."""
        total_received = 0
        try:
            while True:
                data_bytes = recv_all(self.sock, 512000)
                if not data_bytes:
                    logger.error("recv_all returned None")
                    break
                total_received += len(data_bytes) // 8
                self.data_handler(data_bytes)
        except RuntimeError as e:
            logger.debug('Socket closed')
        finally:
            logger.debug(f"Total Received: {total_received}")
            self.sock.close()
            numpy_segment = np.frombuffer(self.segment, dtype=np.complex64)
            numpy_segment.tofile('test.bin')
            
    def data_handler(self, data_bytes):
        # data = np.frombuffer(data_bytes, dtype=np.complex64)
        self.segment += data_bytes
    

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
    
    client = UHD_Client(client_socket)

    try:
        client_socket.connect(server_address)
        client.receive_data()
    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")
    except KeyboardInterrupt:
        print("Client interrupted. Exiting...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
