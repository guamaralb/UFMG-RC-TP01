import socket
import time
import sys
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess
from rich import print

SIZE = 1024
SAW_TRIES = 3

class ClientSocket:
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.max_tries = None
        self.try_count = 0
        self.last_try_numseq = -2
        self.pwd_size = -1
        
        self.soc.settimeout(1.0)
        
        
    def __enter__(self):
        return self
    
    
    def __exit__(self, exc_type, exc, tb):
        self.soc.close()
        
        
    def connect_to_server(self):
        self.soc.connect(self.server_addr)
        
    def close(self):
        self.soc.close()
        
    ##################################################
    # SEND
    ##################################################
    def sendto_server(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.server_addr)
        return send_status
        
            
    ##################################################
    # RECEIVE
    ##################################################
    def _recvfrom(self):
        pckt_bytes, server_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass.try_create_from_bytes(pckt_bytes)
        if pckt is None:
            socket.timeout("malformed packet")
        return pckt, server_addr
    
    def recv_res_to_hel(self):
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
        pckt, server_addr = self._recvfrom()
        return pckt
    
    def recv_res_to_bye(self):
        pckt, server_addr = self._recvfrom()
        return pckt
    
    def validate_res_to_hel(self, pckt: PacketClass):
        if True:
            self.max_tries = pckt.numseq
            self.pwd_size = pckt.pwd_guess.txt.count("?")
            return True


    def validate_res_to_try(self, pckt: PacketClass):
        if True:
            return True


    def validate_res_to_bye(self, pckt: PacketClass):
        if True:
            return True
    
    def generate_hel_pckt(self):
        hel_pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        
        return hel_pckt

    def generate_try_pckt(self, pwd_guess_txt):
        
        self.try_count += 1
        numseq = self.try_count
        self.last_try_numseq = numseq
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        try_pckt = PacketClass(
            type=TYPE_ENUM.TRY,
            numseq=self.try_count,
            pwd_guess=pwd_guess
        )
        return try_pckt

    def generate_bye_pckt(self):
        bye_pckt = PacketClass(
            type=TYPE_ENUM.BYE,
            numseq=self.last_try_numseq,
        )
        return bye_pckt

    def get_new_guess(self):
        
        pwd_guess_txt = sys.stdin.readline().strip()
        
        if pwd_guess_txt == "|":
            sys.exit()
            
        while(len(pwd_guess_txt) < self.pwd_size):
            pwd_guess_txt += " "

        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_txt)
        
        return pwd_guess


def main():
    [_, host, port] = sys.argv
    port = int(port)

    server_addr = (host, port)

    with ClientSocket(server_addr) as client:
        client.connect_to_server()
        
        hel_pckt = client.generate_hel_pckt()
        
        for i in range(SAW_TRIES):
            try:
                send_status = client.sendto_server(hel_pckt)
                res_to_hel_pckt = client.recv_res_to_hel()
            
                if client.validate_res_to_hel(res_to_hel_pckt):
                    max_tries = client.max_tries
                    print(f"NA={client.pwd_size}, NT={client.max_tries}")
                    break
                else:
                    print("CLIENT error validating RES to HEL")
                
            except socket.timeout as msg:
                if i == SAW_TRIES - 1:
                    print("NO RES")
                    sys.exit()
                else:
                    continue
                
            except ConnectionRefusedError as msg:
                print("CONNECTION REFUSED")
                sys.exit()

        tries_success = 0
        while tries_success < max_tries - 1:
            pwd_guess = client.get_new_guess()
            
            try_pckt = client.generate_try_pckt(pwd_guess.txt)
            res_to_try_pckt = None

            for j in range(SAW_TRIES):
                try:
                    send_status = client.sendto_server(try_pckt)
                    res_to_try_pckt = client.recv_res_to_try()
                    break

                except socket.timeout:
                    if j == SAW_TRIES - 1:
                        print("NO RES")
                        sys.exit()

                except ConnectionRefusedError:
                    print("CONNECTION REFUSED")
                    sys.exit()

            if res_to_try_pckt.type == TYPE_ENUM.ERR:
                if res_to_try_pckt.numseq > 0:
                    print(f"RETRY {res_to_try_pckt.numseq}")
                    client.try_count -= 1  # desfaz incremento: retry usa o mesmo numseq
                else:
                    print("ERRO")
                    sys.exit()
                continue

            pattern = res_to_try_pckt.pwd_guess.txt[:client.pwd_size]
            print(f"{client.try_count}({res_to_try_pckt.numseq}) {pattern}")
            tries_success += 1

            if pattern == "*" * client.pwd_size:
                break

        bye_pckt = client.generate_bye_pckt()
                        
        for i in range(SAW_TRIES):
            try:
                send_status = client.sendto_server(bye_pckt)
                res_to_bye_pckt = client.recv_res_to_bye()
            
                if client.validate_res_to_bye(res_to_bye_pckt):
                    pwd_answer = res_to_bye_pckt.pwd_guess.txt[:client.pwd_size]
                    print(f"Senha={pwd_answer}")
                    break
                else:
                    print("CLIENT error validating RES to BYE")
                    
                    
            except socket.timeout as msg:
                if i == SAW_TRIES - 1:
                    print("NO RES")
                    sys.exit()
                else:
                    continue
                
            except ConnectionRefusedError as msg:
                print("CONNECTION REFUSED")
                sys.exit()
        client.close()
        

if __name__ == '__main__':
    main()