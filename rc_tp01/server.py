import socket
import sys
HOST = '0.0.0.0'
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess

SIZE = 1024

class ServerSocket:
    def __init__(self, pwd_txt, nt):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pwd_txt = pwd_txt
        self.nt = int(nt)
        self.pwd_size = len(pwd_txt)
        print("SERVER created")
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.soc.close()

    def bind(self, addr):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind(addr)
        print("SERVER binded to: ", addr)
        
    def _recvfrom(self):
        pckt_bytes, client_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass(pckt_bytes=pckt_bytes)
        print("SERVER received: ", pckt.txt())
        return pckt, client_addr

    def recv_hel(self):
        print("SERVER receiving HEL")
        pckt, client_addr = self._recvfrom()
        self._set_client(client_addr)
        return pckt
    
    def _set_client(self, client_addr):
        self.client_addr = client_addr
        print("SERVER client set:", client_addr)
        
    def _sendoto_client(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.client_addr)
        print("SERVER pckt sent: ", pckt.bytes)
        return send_status
    
    def validate_hel(self, pckt):
        print("SERVER HEL validated")
        return True

    def send_res_to_hel(self):
        print("SERVER sending RES to HEL")
        pwd_guess_sample = ""
        
        while len(pwd_guess_sample) < self.pwd_size:
            pwd_guess_sample = pwd_guess_sample + "?"

        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_sample)
        pckt = PacketClass(type=TYPE_ENUM.RES, seqnum=self.nt, pwd_guess=pwd_guess)
        print("a2")
        
        print(f"NA={1}, NT={pckt.seqnum}")
        
        self._sendoto_client(pckt)


    

def main():
    [_, port, pwd_txt, nt] = sys.argv
    port = int(port)
    
    addr = (HOST, port)
    pwd_size = len(pwd_txt)
    
    PwdGuess.pwd_size = len(pwd_txt)
    
    print(PwdGuess.pwd_size)
    with ServerSocket(pwd_txt=pwd_txt, nt=nt) as server:
    
        server.bind(addr)
        
        while True:
            pckt = server.recv_hel()
            
            if server.validate_hel(pckt):
                send_status = server.send_res_to_hel()
                
            
            
if __name__ == '__main__':
    main()