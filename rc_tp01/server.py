import socket
import sys
HOST = '0.0.0.0'
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess

SIZE = 1024

class ServerSocket:
    def __init__(self, pwd_answer_txt, max_tries):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pwd_answer_txt = pwd_answer_txt
        self.max_tries = int(max_tries)
        self.pwd_size = len(pwd_answer_txt)
        print("SERVER created")
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.soc.close()

    def bind(self, addr):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind(addr)
        print("SERVER binded to: ", addr)

    def _set_client(self, client_addr):
        self.client_addr = client_addr
        print("SERVER client set:", client_addr)
    
    def close(self):
        self.soc.close()
        print("SERVER socket closed")

    ##################################################
    # SEND
    ##################################################
    def sendto_client(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.client_addr)
        print("SERVER pckt sent: ", pckt.bytes)
        return send_status

    ##################################################
    # RECEIVE
    ##################################################
    def _recvfrom(self):
        pckt_bytes, client_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass(pckt_bytes=pckt_bytes)
        print("SERVER received: ", pckt.txt())
        return pckt, client_addr

    def recv_hel(self):
        print("SERVER waiting for HEL")
        pckt, client_addr = self._recvfrom()
        self._set_client(client_addr)
        return pckt

    def recv_try(self):
        print("SERVER waiting for TRY")
        pckt, client_addr = self._recvfrom()
        self._set_client(client_addr)
        return pckt
            
    ##################################################
    # VALIDATE
    ##################################################
    def validate_hel_pckt(self, pckt):
        if True:
            print("SERVER HEL validated")
            return True

    def validate_try_pckt(self, pckt):
        if True:
            print("SERVER TRY validated")
            return True

    def validate_bye_pckt(self, pckt):
        if True:
            print("SERVER BYE validated")
            return True

    ##################################################
    # PCKT GENERATORS
    ##################################################
    def generate_pkct_res_to_hel(self):
        print("SERVER generating RES to HEL pckt")
        pwd_guess_sample = "?" * self.pwd_size + " " * (8 - self.pwd_size)
        
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_sample)
        res_to_hel_pckt = PacketClass(type=TYPE_ENUM.RES, seqnum=self.max_tries, pwd_guess=pwd_guess)
        return res_to_hel_pckt
    
    def generate_pkct_res_to_try(self, pckt_try: PacketClass):
        print("SERVER generating RES to TRY pckt")
        try_seqnum = pckt_try.seqnum
        
        pwd_answer_to_try_txt = self._generate_answer_to_pwd_guess(pckt_try.pwd_guess)
        
        pwd_answer_to_try = PwdGuess(pwd_guess_txt=pwd_answer_to_try_txt)
             
        res_to_try_seqnum = self.max_tries - try_seqnum

        res_to_try_pckt = PacketClass(
            type=TYPE_ENUM.RES,
            seqnum=res_to_try_seqnum,
            pwd_guess=pwd_answer_to_try
        )

        return res_to_try_pckt
    
    def generate_pkct_res_to_bye(self, pckt_bye: PacketClass):        
        print("SERVER generating RES to BYE pckt")        
        
        pwd_answer_to_bye = PwdGuess(pwd_guess_txt=self.pwd_answer_txt)
             
        res_to_bye_pckt = PacketClass(
            type=TYPE_ENUM.RES,
            seqnum=-1,
            pwd_guess=pwd_answer_to_bye
        )

        return res_to_bye_pckt
    
    ##################################################
    # OTHER
    ##################################################
    def _generate_answer_to_pwd_guess(self, pwd_guess: PwdGuess):
        pwd_guess_txt = pwd_guess.txt
        print(type(pwd_guess_txt), pwd_guess_txt)
        pwd_answer_to_try_txt = ["."] * self.pwd_size        
        
        for i in range(self.pwd_size):
            
            if self.pwd_answer_txt[i] == pwd_guess_txt[i]:
                pwd_answer_to_try_txt[i] = "*"
            
            elif pwd_guess_txt[i] in self.pwd_answer_txt:
                pwd_answer_to_try_txt[i] = "+"
            
            else:  
                pwd_answer_to_try_txt[i] = "-"

        pwd_answer_to_try_txt = "".join(pwd_answer_to_try_txt)
        
        return pwd_answer_to_try_txt
        
def main():
    [_, port, pwd_answer_txt, max_tries] = sys.argv
    port = int(port)
    
    addr = (HOST, port)
    pwd_size = len(pwd_answer_txt)
    
    PwdGuess.pwd_size = pwd_size
    
    with ServerSocket(pwd_answer_txt=pwd_answer_txt, max_tries=max_tries) as server:
    
        server.bind(addr)
        
        hel_pckt = server.recv_hel()
        
        if server.validate_hel_pckt(hel_pckt):
            res_to_hel_pckt = server.generate_pkct_res_to_hel()
            send_status = server.sendto_client(res_to_hel_pckt)
        
        while True:
            try_or_bye_pckt = server.recv_try()
            
            if try_or_bye_pckt.type.name == "TRY":        
                if server.validate_try_pckt(try_or_bye_pckt):
                    res_to_try_pckt = server.generate_pkct_res_to_try(try_or_bye_pckt)
                    send_status = server.sendto_client(res_to_try_pckt)
                else:
                    print("SERVER error validating TRY pckt")
                    print("SERVER error validanting TRY pckt")
            
            elif try_or_bye_pckt.type.name == "BYE":
                if server.validate_bye_pckt(try_or_bye_pckt):
                    res_to_bye_pckt = server.generate_pkct_res_to_bye(try_or_bye_pckt)
                    send_status = server.sendto_client(res_to_bye_pckt)
                    server.close()
                    break
                    
                else:
                    print("SERVER error validanting BYE pckt")

            
if __name__ == '__main__':
    main()