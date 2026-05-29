import socket
import time
import sys
from packet import Packet

class PwdGuess():
    def __init__(self, pwd_guess: str):
        self._validate_pwd_guess()
        self.pwd_guess = pwd_guess
    
    def _validate_pwd_guess(self):
        return len(self.pwd_guess) == 8


class ClientSocket:
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.soc.settimeout(1.0)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.soc.close()
        
    def connect_to_server(self):
        self.soc.connect(self.server_addr)
    
    def _sendto_server(self, pckt: Packet):
        pckt_bytes = pckt.pack()
        send_status = self.soc.sendto(pckt_bytes, self.server_addr)
        return send_status
        
    def send_first_msg(self):
        pckt = Packet('HEL', 0, None)
        self._sendto_server(pckt)
        
    def recvfrom(self):
        data_bytes = self.soc.recvfrom(1024)
        return data_bytes
    
def main():
    [_, host, port] = sys.argv
    port = int(port)
    
    server_addr = tuple([host, port])
    
    with ClientSocket(server_addr) as client:
        
        print("CLIENT created")
        
        client.connect_to_server()
        print("CLIENT connected to server: ", server_addr)
        
        msg = b"test"
        client.send_first_msg()
        print("CLIENT Sent: ", msg)

if __name__ == '__main__':
    main()