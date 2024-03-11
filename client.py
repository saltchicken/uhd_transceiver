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
    
class FileSaver():
    def __init__(self, client_generator):
        self.client = client_generator
        self.segment = []
        
    def __enter__(self):
        if not self.client:
            return None
        while True:
            data = self.client.next()
            if len(data) == 0:
                logger.error("Nothing returned. Needs to close")
                break
            else:
                self.segment.append(data)
        self.save()
           
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting FileSaver')
        
    def save(self):
        result = np.concatenate(self.segment)
        result.tofile('received_samples.bin')
        logger.info(f"Saved: {len(result)} samples to received_samples.bin")
        
    
class FFTAnimation():
    def __init__(self, client_generator):
        self.client = client_generator
        
    def __enter__(self):
        if not self.client:
            return None
        
        init_data = np.zeros(1024, dtype=np.complex64)
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 1024)
        self.ax.set_ylim(0,1)
        self.line, = self.ax.plot(init_data)
        
        def update(frame):
            toc = time.perf_counter()
            data = self.client.next()
            if len(data) == 0:
                logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
                self.ani.event_source.stop()
                plt.close()
                return self.line,
            else:
                fft_result = np.fft.fft(data, n=1024)
                fft_result = np.fft.fftshift(fft_result)
                fft_result = np.abs(fft_result)
                self.line.set_ydata(fft_result)
                logger.debug(f"Update takes this much time: {time.perf_counter() - toc}")
                return self.line,
            
        self.ani = FuncAnimation(self.fig, update, blit=True, interval=0)  
        return self
            
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting FFTAnimation')
        
    def show(self):
        plt.show()
        
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
                logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
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
    
    # with SampleGenerator(server_addr) as client:
    #     with Animation(client) as animation:
    #         # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #         animation.show()
    #         time.sleep(0.2)
    #         # embed()
    
    
    # with SampleGenerator(server_addr) as client:
    #     with FileSaver(client) as animation:
    #         # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #         embed()
    
    with SampleGenerator(server_addr) as client:
        with FFTAnimation(client) as animation:
            # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
            animation.show()
            time.sleep(0.2)
            # embed()
    
if __name__ == "__main__":
    main()
