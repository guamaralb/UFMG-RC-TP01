# GUSTAVO AMARAL BERNARDINO

import socket
import sys
HOST = '0.0.0.0'
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess

SIZE = 1024

# Classe que representa o socket do servidor, com os metodos de bind,
# envio e recebimento, e geração de pacotes de resposta
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

    # Método de bind do socket com reutilização de endereço habilitada
    def bind(self, addr):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind(addr)

    # Armazena o endereço do cliente
    def _set_client(self, addr):
        self.client_addr = addr

    def close(self):
        self.soc.close()

    # Método genérico de envio para o cliente
    def sendto_client(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.client_addr)
        return send_status

    # Método genérico de recebimento, tenta converter os bytes em pckt
    def _recvfrom(self):
        data, addr = self.soc.recvfrom(SIZE)
        p = PacketClass.try_create_from_bytes(data)
        return p, addr

    # Método de recebimento do HEL, fica em loop até receber um pckt coerente
    def recv_hel(self):
        while True:
            p, addr = self._recvfrom()
            if p is not None:
                self._set_client(addr)
                return p

    # Método de recebimento dos TRY/BYE enviados pelo cliente, aceita pckt errados
    def recv_try(self):
        p, addr = self._recvfrom()
        if p is not None:
            self._set_client(addr)
        return p

    # Método que gera a RES ao HEL com NT e a dica com '?' indicando tamanho da senha
    def generate_pkct_res_to_hel(self):

        # Preenche o campo de senha com '?'
        sample = "?" * self.pwd_size + " " * (8 - self.pwd_size)
        pg = PwdGuess(pwd_guess_txt=sample)
        return PacketClass(type=TYPE_ENUM.RES, numseq=self.max_tries, pwd_guess=pg)

    # Método que gera a RES para um TRY, calculando o padrão de resposta
    # e o numseq como NT - numseq do TRY
    def generate_pkct_res_to_try(self, pckt_try: PacketClass):
        n = pckt_try.numseq
        pattern = self._generate_pattern_to_pwd_guess(pckt_try.pwd_guess)
        pg = PwdGuess(pwd_guess_txt=pattern)

        numseq_res = self.max_tries - n
        return PacketClass(type=TYPE_ENUM.RES, numseq=numseq_res, pwd_guess=pg)

    # Método que gera a RES para o BYE, com a senha real e numseq -1
    def generate_pkct_res_to_bye(self):
        pg = PwdGuess(pwd_guess_txt=self.pwd_answer_txt)
        return PacketClass(type=TYPE_ENUM.RES, numseq=-1, pwd_guess=pg)

    # Método que gera o padrão de resposta comparando a tentativa com a senha
    def _generate_pattern_to_pwd_guess(self, pwd_guess: PwdGuess):

        # Compara a tentativa com a senha esperada
        guess = pwd_guess.txt
        res = ["."] * self.pwd_size
        for i in range(self.pwd_size):
            if self.pwd_answer_txt[i] == guess[i]:
                res[i] = "*"
            elif guess[i] in self.pwd_answer_txt:
                res[i] = "+"
            else:
                res[i] = "-"
        return "".join(res)


def main():
    [_, port, pwd_answer_txt, max_tries] = sys.argv
    port = int(port)
    addr = (HOST, port)
    PwdGuess.pwd_size = len(pwd_answer_txt)

    with ServerSocket(pwd_answer_txt=pwd_answer_txt, max_tries=max_tries) as server:
        server.bind(addr)

        last_numseq = 0
        last_sent = None

        # HEL: Recebe e valida o HEL e envia a RES
        hel = server.recv_hel()
        ok, err = hel.is_valid(numseq=0)
        if ok:
            last_numseq = hel.numseq
            r = server.generate_pkct_res_to_hel()
            last_sent = r
            send_status = server.sendto_client(r)
        else:
            pass

        # LOOP PRINCIPAL: Recebe as mensagens de TRY e BYE
        while True:
            pckt = server.recv_try()

            if pckt is None:
                continue

            # Identifica se é preciso enviar novamente o ultimo pacote
            if pckt.numseq == last_numseq and pckt.type != TYPE_ENUM.BYE:
                server.sendto_client(last_sent)
                continue

            if pckt.type.name == "TRY":
                
                # Valida o pckt TRY de acordo com as regras
                valid, err = pckt.is_valid(numseq=last_numseq + 1,
                                            max_tries=server.max_tries)
                if valid:
                    r = server.generate_pkct_res_to_try(pckt)
                    send_status = server.sendto_client(r)
                    last_numseq = pckt.numseq
                    last_sent = r
                elif err is not None:
                    
                    # Envia o ERR nos casos que o TRY teve algum erro
                    e = PacketClass(type=TYPE_ENUM.ERR, numseq=err)
                    send_status = server.sendto_client(e)
                    last_sent = e
                    
                # Valida o pckt BYE de acordo com as regras
            elif pckt.type.name == "BYE":
                valid, err = pckt.is_valid(numseq=last_numseq)
                if valid:
                    r = server.generate_pkct_res_to_bye()
                    send_status = server.sendto_client(r)
                    last_numseq = pckt.numseq
                    last_sent = r
                    server.close()
                    break
                elif err is not None:
                    e = PacketClass(type=TYPE_ENUM.ERR, numseq=err)
                    send_status = server.sendto_client(e)
                    last_sent = e

            server.numseq += 1


if __name__ == '__main__':
    main()
