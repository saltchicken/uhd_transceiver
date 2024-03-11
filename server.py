import configparser
import socket
import threading
import numpy as np
import sys, os

import uhd
from loguru import logger

from IPython import embed

from numpysocket import NumpySocket

import configargparse


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
        
        self.remote = args.remote
        self.rx_port = args.rx_port
        
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

        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [0]
        self.rx_metadata = uhd.types.RXMetadata()
        self.rx_streamer = self.usrp.get_rx_stream(st_args)

        
        
        self.buffer_size = 2000
        self.recv_buffer = np.zeros((1, self.buffer_size), np.complex64)
        self.num_samps = 64000
        self.samples = np.zeros(64000, dtype=np.complex64)
        
    def read(self):
        for i in range(self.num_samps//self.buffer_size):
            self.rx_streamer.recv(self.recv_buffer, self.rx_metadata)
            self.samples[i*self.buffer_size:(i+1)*self.buffer_size] = self.recv_buffer[0]
        if not self.rx_metadata.error_code == uhd.types.RXMetadataErrorCode.none:
            logger.warning(self.rx_metadata.error_code)
        return self.samples
        
    def send(self, data):
        samps_sent = self.tx_streamer.send(data, self.tx_metadata)
        
    def start_rx_node(self):
        self.rx_node = RX_Node(self)
        self.rx_node.start()
        
    def start_rx_node_forever(self):
        try:
            while True:
                # TODO: Is creation of new thread inefficient. Can we reuse the same thread.
                self.rx_node = RX_Node(self)
                self.rx_node.start()
                self.rx_node.join()
        except KeyboardInterrupt as e:
            logger.info("Keyboard interrupt hit")
    
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
        self.kill_rx = threading.Event()
        # self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.server_socket.bind(('0.0.0.0', receiver.rx_port)) if receiver.remote else self.server_socket.bind(('localhost', receiver.rx_port))
        # self.server_socket.listen(1)
        
        self.server_socket = NumpySocket()
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', receiver.rx_port))
        self.server_socket.listen()

        logger.info("Waiting for a connection...")
        self.conn, self.addr = self.server_socket.accept()
        logger.info(f"Connected to: {self.addr}")
    
    def run(self):
        """Send continuous stream of data."""
        
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        # INIT_DELAY = 0.05
        # stream_cmd.time_spec = uhd.types.TimeSpec(self.usrp.get_time_now().get_real_secs() + INIT_DELAY)
        stream_cmd.stream_now = True
        self.receiver.rx_streamer.issue_stream_cmd(stream_cmd)
        # sent_packets = []
        
        while not self.kill_rx.is_set():
            data = self.receiver.read()
            try:
                self.conn.sendall(data)
            except ConnectionResetError:
                logger.warning('Connection reset by client')
                break
            # sent_packets.append(np.copy(data))
        
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.receiver.rx_streamer.issue_stream_cmd(stream_cmd)
        self.conn.close()
        self.server_socket.close()
        logger.debug('Conn and socket closed')
        
        # sent_samples = np.concatenate(sent_packets)
        # logger.debug(f"Total sent: {len(sent_samples)}")
        # sent_samples.tofile('sent_samples.bin')
        # logger.debug(f"{len(sent_samples)} written to sent_samples.bin")
    
    def stop(self):
        self.kill_rx.set()
        
def main():
    
    parser = configargparse.ArgParser(default_config_files=['conf/server/default.ini'])
    # p.add('-c', '--my-config', is_config_file=True, help='config file path')
    # TODO: Add specific choices for sample_rate
    parser.add('--tx_sample_rate', type=float, required=True, help="Sample rate for TX (Hz). Example: 2e6")
    parser.add('--tx_center_freq', type=float, required=True, help="Center frequency for TX (Hz). Example: 434e6")
    parser.add('--tx_channel_freq', type=float, required=True, help="Channel frequency for transmitter. Offset from center (Hz). Example: 25000")
    # parser.add_argument('--tx_antenna', type=str, help="")
    parser.add('--tx_gain', type=int, required=True, help="Gain for TX. Example: 10")
    
    parser.add('--rx_sample_rate', type=float, required=True, help="Sample rate for RX (Hz). Example: 2e6")
    parser.add('--rx_center_freq', type=float, required=True, help="Center frequency for receiver (Hz). Example: 434e6")
    parser.add('--rx_channel_freq', type=float, required=True, help="Channel frequency for receiver. Offset from center (Hz). Example: 40000")
    # parser.add_argument('--rx_antenna', type=str, help="")
    parser.add('--rx_gain', type=int, required=True, help="Gain for RX. Example: 20")
    parser.add('--verbose', '-v', action='store_true', help="Enable verbose mode")
    parser.add('--remote', '-r', action='store_true', help="Enable remote access")
    parser.add('--rx_port', type=int, default=12345, help="Server port for RX Node")

    args = parser.parse_args()



    logger.remove()
    logger.add(sys.stderr, level="DEBUG") if args.verbose else logger.add(sys.stderr, level="INFO")
    
    transceiver = Transceiver(args)
    embed(quiet=True)


if __name__ == "__main__":
    main()