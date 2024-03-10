import argparse
import socket
import sys
import time
import numpy as np

from loguru import logger

from numpysocket import NumpySocket

from abc import ABC, abstractmethod

from IPython import embed

class Handler(ABC):
    @abstractmethod
    def handler(self, data: np.ndarray):
        """
        Handle incoming streaming from Client receive_data
        """
        pass
    
    @abstractmethod
    def save(self):
        """
        Run this function after stream has been ended
        """
        pass
    
class SaveToFile(Handler):
    def __init__(self):
        self.segment = []
    
    def handler(self, data: np.ndarray):
        self.segment.append(data)
        
    def save(self):
        result = np.concatenate(self.segment)
        result.tofile("received_samples.bin")
        logger.debug(f"{len(result)} samples writtien to received_samples.bin")


# TODO: Figure out what this should return on loop end
class UHD_Client():
    def __init__(self, remote, port):
        self.server_address = (remote, port) if remote else ('localhost', port)
        
    def receive_data(self, handler: Handler):
        """Receive continuous stream of data."""
        
        with NumpySocket() as sock:
            try:
                sock.connect(self.server_address)
            except ConnectionRefusedError:
                logger.warning("Connection refused. Make sure the server is running.")
                return
            try:
                while True:
                    data = sock.recv()
                    if len(data) == 0:
                        logger.warning(f"data returned with len 0. Breaking receive loop")
                        break
                    handler.handler(data)
            except RuntimeError as e:
                print(e)
            except KeyboardInterrupt:
                logger.warning("Client interrupted. Exiting...")
            finally:
                handler.save()
    

def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    
    handler = SaveToFile()
    client = UHD_Client(args.remote, args.port)
    client.receive_data(handler)
    # embed()

    


if __name__ == "__main__":
    main()
