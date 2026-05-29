import socket
import sys
HOST = 'localhost'

class ServerSocket:
    def __init__(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.soc.close()

    def bind(self, addr):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind(addr)
        
    def recvfrom(self, size):
        data_bytes, addr = self.soc.recvfrom(size)
        
        return data_bytes, addr

    def set_client(self, client_addr):
        self.client_addr = client_addr
        
    def sendto(self, msg):
        send_status = self.soc.sendto(msg, self.client_addr)
        return send_status

def main():
    [_, port, pwd, nt] = sys.argv
    port = int(port)
    
    addr = (HOST, port)
    
    with ServerSocket() as server:
        print("SERVER created")
    
        server.bind(addr)
        print("SERVER binded to: ", addr)
        
        while True:        
            data_bytes, client_addr = server.recvfrom(1024)
            print("SERVER Received: ", data_bytes)
            server.set_client(client_addr)
            
            send_status = server._sendto(data_bytes)
            print("SERVER Sent: ", data_bytes)
            
if __name__ == '__main__':
    main()