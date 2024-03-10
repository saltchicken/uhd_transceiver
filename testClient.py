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
        
class LinePlotter(Handler):
    def __init__(self):
        self.segment = []
        
    def handler(self, data: np.ndarray):
        self.segment.append(data)
        
    def save(self):
        result = np.concatenate(self.segment)
        import matplotlib.pyplot as plt
        plt.style.use('dark_background')
        logger.info(f"Showing a segment with length of {result.shape}")
        plt.plot(result)
        plt.show()
        
class FFTPlotter(Handler):
    def __init__(self):
        self.segment = []
        
    def handler(self, data: np.ndarray):
        self.segment.append(data)
        
    def save(self):
        result = np.concatenate(self.segment)
        import matplotlib.pyplot as plt
        plt.style.use('dark_background')
        
        fft_result = np.fft.fft(result)
        fft_result = np.fft.fftshift(fft_result)
        fft_result = np.abs(fft_result)
        
        # TODO: How do I pass the sample_rate to here. Do we bring back the Segment class?
        freq_bins = np.fft.fftshift(np.fft.fftfreq(len(result))) * 2_000_000 // 1000 # khz
        
        plt.plot(freq_bins, fft_result)
        plt.show()
        
# class Animation(Handler):
#     def __init__(self):
#         import matplotlib.pyplot as plt
#         from matplotlib.animation import FuncAnimation
#         self.fig, self.ax = plt.subplots()
        
#         self.data = np.zeros(64000, dtype=np.complex64)
#         self.line, = self.ax.plot(self.data)
        
#         def update(frame, line, data):
#             print('updating')
#             line.set_ydata(data)
#             return line,
        
#         self.ani = FuncAnimation(self.fig, update, interval=100, fargs=(self.line, self.data))
        
#         plt.show()
                
#     def handler(self, data: np.ndarray):
#         self.data = data
#         print('handling')
#         self.ani.event_source.start()
        
#     def save(self):
#         pass

# TODO: Figure out what this should return on loop end
class UHD_Client():
    def __init__(self, remote, port, sample_rate):
        self.server_address = (remote, port) if remote else ('localhost', port) 
        self.sample_rate = sample_rate
        
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
    

class ClientGenerator():
    def __init__(self, remote, port, sample_rate):
        self.server_address = (remote, port) if remote else ('localhost', port) 
        self.sample_rate = sample_rate
        
    
    def __enter__(self):
        logger.debug('Connecting to numpy socket')
        self.sock = NumpySocket()
        try:
            self.sock.connect(self.server_address)
        except ConnectionRefusedError:
            logger.warning("Connection refused. Make sure the server is running.")
            del self.sock
            return None
        return self
    
    def __exit__(self, *args, **kwargs):
        logger.debug("Exiting ClientGenerator")
        self.sock.close()
        
    def next(self):
        data = self.sock.recv()
        if len(data) == 0:
            logger.error('Fatal error with receiving data')
            return None
        else:
            return data
        
class Animation():
    def __init__(self, client_generator):
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation
        
        self.client = client_generator
        if not self.client:
            return None
        init_data = np.zeros(64000, dtype=np.complex64)
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(-1,2)
        self.line, = self.ax.plot(init_data)
        
        
        
        # def init():
        #     print('init Animation')
        #     return self.line,
            
        def update(frame):
            data = self.client.next()
            print(data)
            self.line.set_ydata(data)
            return self.line,
        
        self.ani = FuncAnimation(self.fig, update, blit=True, interval=0)
        
        plt.show()
    


def main():
    parser = argparse.ArgumentParser(description="Arguments for setting up client of UHD_Transceiver")
    parser.add_argument('--remote', type=str, default='', help="Remote address of UHD_Transceiver server")
    parser.add_argument('--port', type=int, default=12345, help="Remote port of UHD_Transceiver server")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    
    # handler = SaveToFile()
    # handler = LinePlotter()
    # handler = FFTPlotter()
    # client = UHD_Client(args.remote, args.port, 2e6)
    # client.receive_data(handler)
    with ClientGenerator(args.remote, args.port, 2e6) as client:
        embed()

    


if __name__ == "__main__":
    main()
