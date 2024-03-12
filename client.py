import argparse
import sys
import time
import numpy as np
from functools import partial

from loguru import logger
from numpysocket import NumpySocket
from IPython import embed

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
plt.style.use('dark_background')


def contains_signal(data, threshold):
        # squared_magnitudes = np.square(data).real
        # return np.sum(squared_magnitudes > threshold)
        return np.sum(data > threshold)
    
class Sampler(NumpySocket):
    def __init__(self, addr):
        super().__init__()
        self.addr = addr
        self.connect(self.addr)
        
    def next(self):
        return self.recv()
    
    # TODO: Add static typing for func Callable
    def loop(self):
        try:
            while True:
                data = self.next()
                if len(data) == 0:
                    logger.error("Nothing returned. Needs to close")
                    break
                else:
                    logger.debug("Running loop_func")
                    self.loop_func(data)
        except KeyboardInterrupt as e:
            pass
        except ValueError as e:
            logger.error("Connection needs to be restarted")
        
        self.exit_func() 
        
    def loop_func(self, data):
        pass
    
    def exit_func(self):
        logger.debug("Exiting Sampler loop")
        
class SignalFinder(Sampler):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_func(self, data):
        print('hello')
        
def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    server_addr = (args.remote, args.port) if args.remote else ('localhost', args.port) 
    
    signal_finder = SignalFinder(server_addr)
    signal_finder.loop()
    embed()        
if __name__ == "__main__":
    main()
