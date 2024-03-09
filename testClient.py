import argparse
import socket
import sys
import time
import numpy as np

from loguru import logger

from numpysocket import NumpySocket


class UHD_Client():
    def __init__(self, remote, port):
        server_address = (remote, port) if remote else ('localhost', port)
        self.sock = NumpySocket()
        try:
            self.sock.connect(server_address)
        except ConnectionRefusedError:
            logger.warning("Connection refused. Make sure the server is running.")
        self.segment = []
        self.receive_data()
        
    def receive_data(self):
        """Receive continuous stream of data."""
        try:
            while True:
                data = self.sock.recv()
                if len(data) == 0:
                    logger.warning(f"data returned with len 0. Breaking receive loop")
                    break
                self.data_handler(data)
        except RuntimeError as e:
            print(e)
        except KeyboardInterrupt:
            logger.warning("Client interrupted. Exiting...")
        finally:
            logger.debug('Socket closed')
            self.sock.close()
            result = np.concatenate(self.segment)
            result.tofile("received_samples.bin")
            logger.debug(f"{len(result)} samples writtien to received_samples.bin")
            
    def data_handler(self, data):
        self.segment.append(data)
    

def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    
    
    client = UHD_Client(args.remote, args.port)

    


if __name__ == "__main__":
    main()
