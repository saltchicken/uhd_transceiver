import argparse
import socket
import threading
import numpy as np
import sys

import uhd
from loguru import logger

from IPython import embed


class Transceiver():
    def __init__(self, args):
        self.tx_sample_rate = args.tx_sample_rate
        self.tx_center_freq = args.tx_center_freq
        self.tx_channel_freq = args.tx_channel_freq
        # self.tx_antenna = args.tx_antenna
        self.tx_gain = args.tx_gain
        
        self.rx_sample_rate = args.rx_sample_rate
        self.rx_center_freq = args.rx_center_freq
        self.rx_channel_freq = args.rx_channel_freq
        # self.rx_antenna = args.rx_antenna
        self.rx_gain = args.rx_gain
        
        
        self.usrp = uhd.usrp.MultiUSRP()
        self.stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        self.usrp.set_tx_rate(self.tx_sample_rate)
        self.usrp.set_tx_freq(self.tx_center_freq)
        self.usrp.set_tx_gain(self.tx_gain)
        # TODO: Add antenna selection with self.tx_antenna
        self.tx_streamer = self.usrp.get_tx_stream(self.stream_args)
        self.tx_metadata = uhd.types.TXMetadata()
        
        
        self.usrp.set_rx_rate(self.rx_sample_rate, 0)
        self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.rx_center_freq), 0)
        self.usrp.set_rx_gain(self.rx_gain, 0)

        # Set up the stream and receive buffer
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [0]
        self.rx_metadata = uhd.types.RXMetadata()
        self.rx_streamer = self.usrp.get_rx_stream(st_args)
        # recv_buffer = np.zeros((1, self.read_buffer_size), dtype=np.complex64)

        # Start Stream
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        # stream_cmd.stream_now = True
        INIT_DELAY = 0.05
        stream_cmd.time_spec = uhd.types.TimeSpec(self.usrp.get_time_now().get_real_secs() + INIT_DELAY)
        # self.tx_metadata.has_time_spec = bool(self.tx_streamer.get_num_channels())
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
        self.buffer_size = 2000
        self.recv_buffer = np.zeros(self.buffer_size, np.complex64)
        self.num_samps = 64000
        self.samples = np.zeros(64000, dtype=np.complex64)
    def read(self):
        # stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        # stream_cmd.stream_now = True
        # self.rx_streamer.issue_stream_cmd(stream_cmd)
        
        # TODO: Possibly implement this for efficiency if larger buffer needed.
        for i in range(self.num_samps//self.buffer_size):
            self.rx_streamer.recv(self.recv_buffer, self.rx_metadata)
            self.samples[i*1000:(i+1)*1000] = self.recv_buffer[0]
        
        # self.rx_streamer.recv(self.read_buffer, self.rx_metadata)
        if not self.rx_metadata.error_code == uhd.types.RXMetadataErrorCode.none:
            logger.warning(self.rx_metadata.error_code)
        # self.read_buffer = np.copy(self.usrp.recv_num_samps(2000, self.frequency, self.sample_rate, [0], 0))
        # stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        # self.rx_streamer.issue_stream_cmd(stream_cmd)
        return self.samples
        
    def send(self, data):
        samps_sent = self.tx_streamer.send(data, self.tx_metadata)
        
    def start_rx_node(self):
        self.rx_node = RX_Node(self)
        self.rx_node.start()
    
    def stop_rx_node(self):
        self.rx_node.stop()
        
        
class TX_Node(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        pass
        
    
class RX_Node(threading.Thread):
    # TODO: Add static typing
    def __init__(self, receiver):
        threading.Thread.__init__(self)
        self.receiver = receiver
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', 12345))  # Bind to localhost on port 12345
        self.server_socket.listen(1)

        print("Waiting for a connection...")
        self.conn, addr = self.server_socket.accept()
        print("Connected to:", addr)
    
    def run(self):
        """Send continuous stream of data."""
        total_sent = 0
        
        self.conn.setblocking(False)
        try:
            while True:
                # TODO: Does this need to make a copy via np.copy()
                data = self.receiver.read()
                data_bytes = data.tobytes()  # Convert the numpy array to bytes
                print(len(data_bytes))
                self.conn.sendall(data_bytes)  # Send the data to the client
                total_sent += 64000
        except:
            print(f"Total sent: {total_sent}")
            self.conn.close()
    
def main():
    parser = argparse.ArgumentParser(description="A simple script to demonstrate argument parsing.")
    parser.add_argument('--tx_sample_rate', type=float, required=True, help="Sample rate for TX (Hz). Example: 2e6")
    parser.add_argument('--tx_center_freq', type=float, required=True, help="Center frequency for TX (Hz). Example: 434e6")
    parser.add_argument('--tx_channel_freq', type=float, required=True, help="Channel frequency for transmitter. Offset from center (Hz). Example: 25000")
    # parser.add_argument('--tx_antenna', type=str, required=True, help="")
    parser.add_argument('--tx_gain', type=int, required=True, help="Gain for TX. Example: 10")
    
    
    parser.add_argument('--rx_sample_rate', type=float, required=True, help="Sample rate for RX (Hz). Example: 2e6")
    parser.add_argument('--rx_center_freq', type=float, required=True, help="Center frequency for receiver (Hz). Example: 434e6")
    parser.add_argument('--rx_channel_freq', type=float, required=True, help="Channel frequency for receiver. Offset from center (Hz). Example: 40000")
    # parser.add_argument('--rx_antenna', type=str, required=True, help="")
    parser.add_argument('--rx_gain', type=int, required=True, help="Gain for RX. Example: 20")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode")
    args = parser.parse_args()

    logger.remove()
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")
    

    transceiver = Transceiver(args)
    embed(quiet=True)


if __name__ == "__main__":
    main()