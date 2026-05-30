import socket
import time
import sys
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess


SIZE = 1024

class ClientSocket:
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nt = None
        self.try_count = 0
        print("CLIENT created")
        
        
    def __enter__(self):
        return self
    
    
    def __exit__(self, exc_type, exc, tb):
        self.soc.close()
        
        
    def connect_to_server(self):
        self.soc.connect(self.server_addr)
        print("CLIENT connected to server: ", self.server_addr)
    
    
    def _sendto_server(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.server_addr)
        print("CLIENT pckt sent: ", pckt.bytes)
        return send_status
        
        
    def send_hel(self):
        pwd_guess = PwdGuess(" " * 8, is_hel=True)
        print("CLIENT sending HEL")
        pckt = PacketClass(type=TYPE_ENUM.HEL, seqnum=0, pwd_guess=pwd_guess)
        self._sendto_server(pckt)
        
        
    def send_try(self, pwd_guess: PacketClass):
        self.try_count += 1
        print(f"CLIENT sending TRY ({self.try_count})")
        pckt = PacketClass(type=TYPE_ENUM.TRY, seqnum=self.try_count, pwd_guess=pwd_guess)
        self._sendto_server(pckt)
        
        
    def _recvfrom(self):
        print("XXX")
        pckt_bytes, server_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass(pckt_bytes=pckt_bytes)
        print("ZZZ")
        print("CLIENT received: ", pckt.txt())
        return pckt, server_addr
    
    def recv_res_to_hel(self):
        print("CLIENT receiving RES to HEL")
        pckt, server_addr = self._recvfrom()
        
        pwd_size = 0
        
        for c in pckt.pwd_guess.txt:
            if c == "?":
                pwd_size += 1
            else:
                break
        
        PacketClass.pwd_size = pwd_size
        return pckt
    
    def validate_res_to_hel(self, pckt: PacketClass):
        if True:
            self.nt = pckt.seqnum
            return True


    def get_new_guess(self, i, max_attempts, final_password):
        print("CLIENT getting guess from user")
        
        pwd_guess_txt = sys.stdin.readline()
        
        # REMOVER AQUI VVVVVVVVVVVVV
        if i == max_attempts - 1:
            pwd_guess_txt = final_password
        
        else:
            pwd_guess_txt = str(i) * 4  # 0000, 1111, 2222...
        # REMOVER AQUI ^^^^^^^^^^^^^^
        
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        
        return  pwd_guess
    
        


def main():
    [_, host, port] = sys.argv
    port = int(port)

    server_addr = (host, port)

    with ClientSocket(server_addr) as client:
        client.connect_to_server()
        client.send_hel()
        pckt = client.recv_res_to_hel()

        if client.validate_res_to_hel(pckt):

            # agora nt vem do HEL ou do client (ajuste conforme seu código)
            nt = client.nt
            final_pwd = 1234  # precisa estar armazenada após HEL ou config

            for i in range(nt):
                pwd_guess = client.get_new_guess(i, nt, final_pwd)

                client.send_try(pwd_guess)

                res = client.recv_res()

                if "ACERTOU" in res:
                    break                
            
        
        

if __name__ == '__main__':
    main()