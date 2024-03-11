import argparse
import sys
import time
import numpy as np

from loguru import logger

from numpysocket import NumpySocket

from IPython import embed

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

plt.style.use('dark_background')

class SampleGenerator(NumpySocket):
    def __init__(self, addr):
        super().__init__()
        self.connect(addr)
                
    def next(self):
        # TODO: Does this need to make a copy
        return self.recv()
        
class Animation():
    def __init__(self, client_generator):
        self.client = client_generator
        
    def __enter__(self):
        if not self.client:
            return None
        init_data = np.zeros(64000, dtype=np.complex64)
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 64000)
        self.ax.set_ylim(-0.1,0.1)
        self.line, = self.ax.plot(init_data)
        
        def update(frame):
            toc = time.perf_counter()
            data = self.client.next()
            if len(data) == 0:
                logger.error('Fatal error with receiving data')
                logger.debug("Breaking from animation") 
                self.ani.event_source.stop()
                plt.close()
                return self.line,
            else:
                self.line.set_ydata(data)
                logger.debug(f"Update takes this much time: {time.perf_counter() - toc}")
                return self.line,
        
        self.ani = FuncAnimation(self.fig, update, blit=True, interval=0)  
        return self
    
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting Animation')
        
    def show(self):
        plt.show()
        
        
def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    server_addr = (args.remote, args.port) if args.remote else ('localhost', args.port) 
    
    with SampleGenerator(server_addr) as client:
        with Animation(client) as animation:
            # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
            animation.show()
            time.sleep(0.2)
            # embed()
    
if __name__ == "__main__":
    main()
