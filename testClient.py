import socket
import time
import numpy as np
import sys

def receive_data(sock):
    """Receive continuous stream of data."""
    total_received = 0
    try:
        while True:
            data_bytes = sock.recv(512000)  # Receive data from the server
            # data = np.frombuffer(data_bytes)
            if not data_bytes:
                break
            if len(data_bytes) == 512000:
                data = np.frombuffer(data_bytes, dtype=np.complex64)  # Convert received bytes to numpy array
                print(data.shape)
                print("Received:", data)
                total_received += 64000
            else:
                print(len(data_bytes))
            time.sleep(0.031)
    finally:
        print(total_received)
        sock.close()

def main():
    # server_address = ('localhost', 12345)  # Server address and port
    server_address = ('192.168.1.11', 12345)  # Server address and port
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(server_address)  # Connect to the server
        receive_data(client_socket)  # Receive data continuously
    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")
    except KeyboardInterrupt:
        print("Client interrupted. Exiting...")
        sys.exit()
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
