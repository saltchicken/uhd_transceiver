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
from matplotlib.widgets import Slider
plt.style.use('dark_background')

from timer_gen import timer_gen


def contains_signal(data, threshold):
        # squared_magnitudes = np.square(data).real
        # return np.sum(squared_magnitudes > threshold)
        return np.sum(data > threshold)
    
class Sampler(NumpySocket):
    def __init__(self, addr):
        super().__init__()
        self.connect(addr)
        
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
                    self.loop_func(data)
        except KeyboardInterrupt as e:
            pass
        except ValueError as e:
            logger.error("Connection needs to be restarted")
        
        self.loop_exit() 
        
    def loop_func(self, data):
        pass
    
    def loop_exit(self):
        logger.debug("Exiting Sampler loop")
        
class SignalFinder(Sampler):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_func(self, data):
        if contains_signal(data, 0.004):
            logger.debug('Signal found')

class Animator(NumpySocket):
    def __init__(self, addr):
        super().__init__()
        self.connect(addr)
    
    def next(self):
        return self.recv()
    
    def loop(self):
        self.loop_init()
        plt.show()
            
        self.loop_exit()
            
    def loop_init(self):
        pass

    def loop_func(self, frame):
        pass
    
    def loop_exit(self):
        logger.debug("Exiting Animator loop")
        
class Waterfall(Animator):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_init(self):
        iterations = 200
        self.fft_size = 512
        self.waterfall_data = np.zeros((iterations, self.fft_size))
        
        plt.rcParams['toolbar'] = 'None'
        self.fig, self.ax = plt.subplots()
        self.fig.set_size_inches(8, 10)
        
        self.im = self.ax.imshow(self.waterfall_data, cmap='viridis', vmin=-0.1, vmax=3.0)
        
        sample_rate = 2000000
        self.freq_range = sample_rate / 2000 # Half sample_rate and convert to kHz
        # time_domain = buffer_size * iterations * decimator / sample_rate
        self.time_domain = 64000 * iterations / sample_rate
        plt.imshow(self.waterfall_data, extent=[-self.freq_range, self.freq_range, 0, self.time_domain], aspect='auto')
        
        self.ax.set_xlabel('Frequency (kHz)')
        self.ax.set_ylabel('Time (s)')
        self.ax.set_title('Waterfall Plot')
        self.fig.colorbar(self.im, label='Amplitude')
        
        self.ani = FuncAnimation(self.fig, self.loop_func, blit=True, interval=0)
        
    def loop_func(self, frame):
        data = self.next()
        if len(data) == 0:
            logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
            self.ani.event_source.stop()
            plt.close()
            return self.im,
        else:
            freq_domain = np.fft.fftshift(np.fft.fft(data, n=self.fft_size))
            max_magnitude_index = np.abs(freq_domain)
            self.waterfall_data[1:, :] = self.waterfall_data[:-1, :]
            self.waterfall_data[0, :] = max_magnitude_index
            
            self.im.set_array(self.waterfall_data)
            self.im.set_extent([-self.freq_range, self.freq_range, 0, self.time_domain])
            
        return self.im,

class Linegraph(Animator):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_init(self):
        init_data = np.zeros(64000, dtype=np.complex64)
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 64000)
        self.ax.set_ylim(-0.1,0.1)
        self.line, = self.ax.plot(init_data)
        
        self.ani = FuncAnimation(self.fig, self.loop_func, blit=True, interval=0)
        
    def loop_func(self, frame):
        data = self.next()
        if len(data) == 0:
            logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
            self.ani.event_source.stop()
            plt.close()
            return self.line,
        else:
            self.line.set_ydata(data)
            return self.line,
        
class LinegraphSignalFinder(Animator):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_init(self):
        init_data = np.zeros(64000, dtype=np.complex64)
        self.fig, self.ax = plt.subplots()
        plt.subplots_adjust(bottom=0.25)
        self.ax.set_xlim(0, 64000)
        self.ax.set_ylim(-0.1,0.1)
        self.line, = self.ax.plot(init_data)
        
        def on_slider_change(val):
            self.threshold = val
        
        self.threshold_line = self.ax.axhline(y=0.025, color='r', linestyle='--', label='Horizontal Line')
        self.threshold = 0.0
        self.slider_ax = plt.axes([0.125, 0.1, 0.8, 0.05])
        self.slider = Slider(self.slider_ax, 'Threshold', 0.0, 0.1, valinit=self.threshold)
        self.slider.on_changed(on_slider_change)
        
        self.ani = FuncAnimation(self.fig, self.loop_func, blit=True, interval=0)
        
        self.timer = timer_gen()
        
    def loop_func(self, frame):
        data = self.next()
        print(next(self.timer))
        if len(data) == 0:
            logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
            self.ani.event_source.stop()
            plt.close()
            return self.line,
        else:
            self.line.set_ydata(data)
            self.threshold_line.set_ydata(self.threshold)
            if contains_signal(data, self.threshold):
                print('Found signal', end="\r")
            else:
                print('No signal     ', end="\r")
            return self.line, self.threshold_line
        
    
        
def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    server_addr = (args.remote, args.port) if args.remote else ('localhost', args.port) 
    
    # signal_finder = SignalFinder(server_addr)
    # signal_finder.loop()
    # time.sleep(0.2)  
    
    # waterfall = Waterfall(server_addr)
    # waterfall.loop()
    # time.sleep(0.2)
    
    # linegraph = Linegraph(server_addr)
    # linegraph.loop()
    # time.sleep(0.2)
    
    linegraph = LinegraphSignalFinder(server_addr)
    linegraph.loop()
    time.sleep(0.2)

        
if __name__ == "__main__":
    main()
