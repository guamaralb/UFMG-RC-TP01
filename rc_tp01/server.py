import socket
import sys
HOST = '0.0.0.0'
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess
from rich import print

SIZE = 1024

class ServerSocket:
    def __init__(self, pwd_answer_txt: str, max_tries: str):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pwd_answer_txt = pwd_answer_txt
        self.max_tries = int(max_tries)
        self.pwd_size = len(pwd_answer_txt)
        self.numseq = 1
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.soc.close()

    def bind(self, addr):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind(addr)

    def _set_client(self, client_addr):
        self.client_addr = client_addr
    
    def close(self):
        self.soc.close()

    ##################################################
    # SEND
    ##################################################
    def sendto_client(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.client_addr)
        return send_status

    ##################################################
    # RECEIVE
    ##################################################
    def _recvfrom(self):
        pckt_bytes, client_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass.try_create_from_bytes(pckt_bytes)
        return pckt, client_addr

    def recv_hel(self):
        while True:
            pckt, client_addr = self._recvfrom()
            if pckt is not None:
                self._set_client(client_addr)
                return pckt

    def recv_try(self):
        pckt, client_addr = self._recvfrom()
        if pckt is not None:
            self._set_client(client_addr)
        return pckt
        
    ##################################################
    # PCKT GENERATORS
    ##################################################
    def generate_pkct_res_to_hel(self):
        pwd_guess_sample = "?" * self.pwd_size + " " * (8 - self.pwd_size)
        
        pwd_guess = PwdGuess(pwd_guess_txt=pwd_guess_sample)
        res_to_hel_pckt = PacketClass(type=TYPE_ENUM.RES, numseq=self.max_tries, pwd_guess=pwd_guess)
        return res_to_hel_pckt
    
    def generate_pkct_res_to_try(self, pckt_try: PacketClass):
        try_numseq = pckt_try.numseq
        
        pwd_answer_to_try_txt = self._generate_pattern_to_pwd_guess(pckt_try.pwd_guess)
        
        pwd_answer_to_try = PwdGuess(pwd_guess_txt=pwd_answer_to_try_txt)
             
        res_to_try_numseq = self.max_tries - try_numseq

        res_to_try_pckt = PacketClass(
            type=TYPE_ENUM.RES,
            numseq=res_to_try_numseq,
            pwd_guess=pwd_answer_to_try
        )

        return res_to_try_pckt
    
    def generate_pkct_res_to_bye(self):        
        ##print("~SERVER generating RES to BYE pckt")        
        
        pwd_answer_to_bye = PwdGuess(pwd_guess_txt=self.pwd_answer_txt)

        res_to_bye_pckt = PacketClass(
            type=TYPE_ENUM.RES,
            numseq=-1,
            pwd_guess=pwd_answer_to_bye
        )

        return res_to_bye_pckt

    def generate_pkct_err(self, err_numseq: int):
        return PacketClass(
            type=TYPE_ENUM.ERR, 
            numseq=err_numseq
        )
    
    ##################################################
    # OTHER
    ##################################################
    def _generate_pattern_to_pwd_guess(self, pwd_guess: PwdGuess):
        pwd_guess_txt = pwd_guess.txt
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
        
        last_client_numseq = 0
        last_pckt_sent = None
        
        hel_pckt = server.recv_hel()

        hel_is_valid, err_seqnum = hel_pckt.is_valid(numseq=0)

        if hel_is_valid:
            last_client_numseq = hel_pckt.numseq
            res_to_hel_pckt = server.generate_pkct_res_to_hel()
            last_pckt_sent = res_to_hel_pckt
            send_status = server.sendto_client(res_to_hel_pckt)
        
        else:
            
            print("SERVER error validating HEL pckt")
        
        while True:
            try_or_bye_pckt = server.recv_try()
            
            if try_or_bye_pckt.numseq == last_client_numseq and try_or_bye_pckt.type != TYPE_ENUM.BYE:
                server.sendto_client(last_pckt_sent)
                continue

            if try_or_bye_pckt.type.name == "TRY":        
                try_is_valid, err_seqnum = try_or_bye_pckt.is_valid(
                    numseq=last_client_numseq + 1,
                    max_tries=server.max_tries,
                )

                if try_is_valid:
                    res_to_try_pckt = server.generate_pkct_res_to_try(try_or_bye_pckt)
                    send_status = server.sendto_client(res_to_try_pckt)

                    last_client_numseq = try_or_bye_pckt.numseq
                    last_pckt_sent = res_to_try_pckt

                elif err_seqnum is not None:
                    err_pckt = server.generate_pkct_err(err_seqnum)
                    send_status = server.sendto_client(err_pckt)
                    last_pckt_sent = err_pckt

            elif try_or_bye_pckt.type.name == "BYE":
                bye_is_valid, err_seqnum = try_or_bye_pckt.is_valid(
                    numseq=last_client_numseq
                )

                if bye_is_valid:
                    res_to_bye_pckt = server.generate_pkct_res_to_bye()
                    send_status = server.sendto_client(res_to_bye_pckt)

                    last_client_numseq = try_or_bye_pckt.numseq
                    last_pckt_sent = res_to_bye_pckt

                    server.close()
                    break

                elif err_seqnum is not None:
                    err_pckt = server.generate_pkct_err(err_seqnum)
                    send_status = server.sendto_client(err_pckt)
                    last_pckt_sent = err_pckt

            server.numseq += 1
            
if __name__ == '__main__':
    main()