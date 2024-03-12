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
        
class WaterfallAnimation():
    def __init__(self, client_generator):
        self.client = client_generator
        
    def __enter__(self):
        if not self.client:
            return None
        iterations = 200
        fft_size = 512
        waterfall_data = np.zeros((iterations, fft_size))
        
        plt.rcParams['toolbar'] = 'None'
        fig, ax = plt.subplots()
        fig.set_size_inches(8, 10)
        
        
        
        im = ax.imshow(waterfall_data, cmap='viridis', vmin=-0.1, vmax=3.0)
        
        sample_rate = 2000000
        freq_range = sample_rate / 2000 # Half sample_rate and convert to kHz
        # time_domain = buffer_size * iterations * decimator / sample_rate
        time_domain = 64000 * iterations / sample_rate
        plt.imshow(waterfall_data, extent=[-freq_range, freq_range, 0, time_domain], aspect='auto')
        
        ax.set_xlabel('Frequency (kHz)')
        ax.set_ylabel('Time (s)')
        ax.set_title('Waterfall Plot')
        fig.colorbar(im, label='Amplitude')
        
        ##### Performance tracking
        self.frame_toc = time.perf_counter()
        ##### frame is duration of updating FuncAninamation after update returns
        
        def update(frame):
            ##### Performance tracking
            frame_tic =time.perf_counter() - self.frame_toc
            update_toc = time.perf_counter()
            #####
            
            data = self.client.next()
            if len(data) == 0:
                logger.error('Fatal error with receiving data, breaking from animation (Server probably closed)')
                self.ani.event_source.stop()
                plt.close()
                return im,
            else:
                freq_domain = np.fft.fftshift(np.fft.fft(data, n=fft_size))
                max_magnitude_index = np.abs(freq_domain)
                waterfall_data[1:, :] = waterfall_data[:-1, :]
                waterfall_data[0, :] = max_magnitude_index
                
                im.set_array(waterfall_data)
                im.set_extent([-freq_range, freq_range, 0, time_domain])
                
                ##### Performance tracking
                update_tic = time.perf_counter() - update_toc
                logger.debug(f"Update time: { '{:.5f}'.format(update_tic)} | Frame time: { '{:.5f}'.format(frame_tic)}")
                if update_tic + frame_tic > 0.034:
                    logger.warning(f"FuncAnimation taking longer than 34ms (0.034) to update. May have issues with accuracy.")
                self.frame_toc = time.perf_counter()
                #####
                
                return im,
            
        self.ani = FuncAnimation(fig, update, blit=True, interval=0)  
        return self
        
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting WaterfallAnimation')
        
    def show(self):
        plt.show()

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

class SignalFinder_OLD():
    def __init__(self, client_generator):
        self.client = client_generator
        # self.segment = []
    
    def __enter__(self):
        if not self.client:
            return None
        try:
            while True:
                data = self.client.next()
                if len(data) == 0:
                    logger.error("Nothing returned. Needs to close")
                    break
                else:
                    if contains_signal(data, 0.004):
                        logger.debug('Contains signal')
        except KeyboardInterrupt as e:
            pass         
    
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting SignalFinder')
    
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
                    logger.debug("Running loop_func")
                    self.loop_func(data)
        except KeyboardInterrupt as e:
            pass
        finally:
            self.exit_func() 
        
    def loop_func(self, data):
        pass
    
    def exit_func(self):
        logger.debug("Leaving Sampler")
    
class SignalFinderLoopFunc(Sampler):
    def __init__(self, addr):
        super().__init__(addr)
        
    def loop_func(self, data):
        print('hello')
    
class SignalFinderGenerator(SampleGenerator):
    def __init__(self, addr):
        super().__init__(addr)
        if self is None:
            logger.error("This actually happened")
            return None
    
    def __enter__(self):
        try:
            while True:
                data = self.next()
                if len(data) == 0:
                    logger.error("Nothing returned. Needs to close")
                    break
                else:
                    if contains_signal(data, 0.004):
                        logger.debug('Contains signal')
        except KeyboardInterrupt as e:
            pass   
    
    def __exit__(self, *args, **kwargs):
        logger.debug('Exiting SignalFinderGenerator')    
                 
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
    
    # with SampleGenerator(server_addr) as client:
    #     with FFTAnimation(client) as animation:
    #         # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #         animation.show()
    #         time.sleep(0.2)
    #         # embed()
    
    # with SampleGenerator(server_addr) as client:
    #     with WaterfallAnimation(client) as animation:
    #         # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #         animation.show()
    #         time.sleep(0.2)
    #         # embed()
    
    # with SampleGenerator(server_addr) as client:
    #     with SignalFinderGenerator(client) as animation:
    #         # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #         # animation.show()
    #         time.sleep(0.2)
    #         # embed()
    
    # with SignalFinder(server_addr) as client:
    #     # TODO: This allows the script to run a little longer so the cleanup can happen. Add something like join to make sure all threads are complete.
    #     time.sleep(0.2)
    embed()        
if __name__ == "__main__":
    main()
