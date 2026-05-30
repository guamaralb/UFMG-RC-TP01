import socket
import time
import sys
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess


SIZE = 1024

# REMOVER AQUI VVVVVVVVVVVVV
cont = 0

tentativas = [
    "2154",
    "2495",
    "2745",
    "2345"
]
# REMOVER AQUI ^^^^^^^^^^^^^^

class ClientSocket:
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.max_tries = None
        self.try_count = 0
        print("CLIENT created")
        
        
    def __enter__(self):
        return self
    
    
    def __exit__(self, exc_type, exc, tb):
        self.soc.close()
        
        
    def connect_to_server(self):
        self.soc.connect(self.server_addr)
        print("CLIENT connected to server: ", self.server_addr)
        
    def close(self):
        self.soc.close()
        print("CLIENT socket closed")
        
    ##################################################
    # SEND
    ##################################################
    def sendto_server(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.server_addr)
        print("CLIENT pckt sent: ", pckt.txt())
        return send_status
        
            
    ##################################################
    # RECEIVE
    ##################################################
    def _recvfrom(self):
        pckt_bytes, server_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass(pckt_bytes=pckt_bytes)

        print("CLIENT received: ", pckt.txt())
        return pckt, server_addr
    
    def recv_res_to_hel(self):
        print("CLIENT waiting for RES to HEL")
        pckt, server_addr = self._recvfrom()
        
        pwd_size = 0
        
        for c in pckt.pwd_guess.txt:
            if c == "?":
                pwd_size += 1
            else:
                break
        
        PwdGuess.pwd_size = pwd_size
        return pckt
    
    def recv_res_to_try(self):
        print("CLIENT waiting for RES to TRY")
        pckt, server_addr = self._recvfrom()
        return pckt
    
    def recv_res_to_bye(self):
        print("CLIENT waiting for RES to BYE")
        pckt, server_addr = self._recvfrom()
        return pckt
    
    ##################################################
    # VALIDATE
    ##################################################
    def validate_res_to_hel(self, pckt: PacketClass):
        if True:
            print("CLIENT RES to HEL validated")
            self.max_tries = pckt.seqnum
            return True


    def validate_res_to_try(self, pckt: PacketClass):
        if True:
            print("CLIENT RES to TRY validated")
            return True


    def validate_res_to_bye(self, pckt: PacketClass):
        if True:
            print("CLIENT RES to TRY validated")
            return True

    ##################################################
    # PCKT GENERATORS
    ##################################################
    
    def generate_hel_pckt(self):
        print("CLIENT generating HEL pckt")
        pwd_guess = PwdGuess(pwd_guess_txt=" " * 8, is_hel=True)
        hel_pckt = PacketClass(type=TYPE_ENUM.HEL, seqnum=0, pwd_guess=pwd_guess)
        
        return hel_pckt

    def generate_try_pckt(self, pwd_guess_txt):
        self.try_count += 1
        print(f"CLIENT generating TRY ({self.try_count}) pckt ")
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        try_pckt = PacketClass(type=TYPE_ENUM.TRY, seqnum=self.try_count, pwd_guess=pwd_guess)
        return try_pckt

    def generate_bye_pckt(self, pwd_guess_txt):
        self.try_count += 1
        print(f"CLIENT generating BYE ({self.try_count}) pckt ")
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        bye_pckt = PacketClass(
            type=TYPE_ENUM.BYE,
            seqnum=self.try_count,
            pwd_guess=pwd_guess
        )
        return bye_pckt

    ##################################################
    # OTHER
    ##################################################
    def get_new_guess(self, i, max_attempts):
        print("CLIENT getting guess from user")
        
        # pwd_guess_txt = sys.stdin.readline()
        
        # REMOVER AQUI VVVVVVVVVVVVV
        global cont
        global tentativas
        
        pwd_guess = PwdGuess(pwd_guess_txt=tentativas[cont])
        cont += 1
        # REMOVER AQUI ^^^^^^^^^^^^^^
        
        # pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        
        return  pwd_guess
    
        


def main():
    [_, host, port] = sys.argv
    port = int(port)

    server_addr = (host, port)

    with ClientSocket(server_addr) as client:
        client.connect_to_server()
        
        hel_pckt = client.generate_hel_pckt()
        send_status = client.sendto_server(hel_pckt)
        
        res_to_hel_pckt = client.recv_res_to_hel()

        if client.validate_res_to_hel(res_to_hel_pckt):
            max_tries = client.max_tries

            for i in range(max_tries):
                pwd_guess = client.get_new_guess(i, max_tries)
                
                if i < max_tries - 1:
                    try_pckt = client.generate_try_pckt(pwd_guess.txt)
                    send_status = client.sendto_server(try_pckt)
                    
                    res_to_try_pckt = client.recv_res_to_try()
                    
                    if client.validate_res_to_try(res_to_try_pckt):
                        ...
                    else:
                        print("CLIENT error validating RES to TRY")
                
                else:
                    bye_pckt = client.generate_bye_pckt(pwd_guess.txt)
                    send_status = client.sendto_server(bye_pckt)
                    
                    res_to_bye_pckt = client.recv_res_to_bye()
                    
                    if client.validate_res_to_bye(res_to_bye_pckt):
                        client.close()
                    else:
                        print("CLIENT error validating RES to BYE")
        

if __name__ == '__main__':
    main()