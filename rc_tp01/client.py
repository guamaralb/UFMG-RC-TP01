# GUSTAVO AMARAL BERNARDINO

import socket
import sys
from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess

SIZE = 1024
# SAW = stop and wait
SAW_TRIES = 3

# Classe que representa o socket do cliente
class ClientSocket:
    
    # Inicializa e conecta de uma vez com o servidor
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.max_tries = None
        self.try_count = 0
        self.last_try_numseq = -2
        self.pwd_size = -1
        
        self.soc.settimeout(1.0)
        self.soc.connect(self.server_addr)
        
    # Metodos de enter e exit para garantir que a conexão fecha quando dá erro
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.soc.close()
        
    # Metodo basico para manter a coerencia do main, sem chamar metodos de atributos
    def close(self):
        self.soc.close()
    
    # Método generico de envio, já vinculado ao server
    def sendto_server(self, pckt: PacketClass):
        send_status = self.soc.sendto(pckt.bytes, self.server_addr)
        return send_status
        
    # Método generico de recebimento, chamado por outros metodos especificos por tipo de msg
    def _recvfrom(self):
        pckt_bytes, server_addr = self.soc.recvfrom(SIZE)
        pckt = PacketClass.try_create_from_bytes(pckt_bytes)
        if pckt is None:
            socket.timeout("malformed packet")
        return pckt, server_addr
    
    
    # Método de recebimento do HEL, realiza a verificação da dica da senha (com os "?")
    # Estabelece o tamanho da senha
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
    
    # Método do recebimento de RES para o TRY, generico
    def recv_res_to_try(self):
        pckt, server_addr = self._recvfrom()
        return pckt
    
    # Método do recebimento de RES para o BYE, generico
    def recv_res_to_bye(self):
        pckt, server_addr = self._recvfrom()
        return pckt
    
    # Atualiza os valores de maximo de tentativas e do tamanho da senha
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
    
    # Método para gerar o pckt do HEL, numseq fixo em 0
    def generate_hel_pckt(self):
        hel_pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        
        return hel_pckt

    # Método para gerar o pckt dos TRY, que aumenta o numero de tries
    # e possui numseq variável. Aqui ele precisa inserir a pwd no pckt
    # Ele atualiza também o numseq do ultimo TRY
    def generate_try_pckt(self, pwd_guess: PwdGuess):
        
        self.try_count += 1
        numseq = self.try_count
        self.last_try_numseq = numseq
        try_pckt = PacketClass(
            type=TYPE_ENUM.TRY,
            numseq=self.try_count,
            pwd_guess=pwd_guess
        )
        return try_pckt

    # Método para gerar o pckt do BYE, que tem o numseq vinculado ao ultimo
    # enviado
    def generate_bye_pckt(self):
        bye_pckt = PacketClass(
            type=TYPE_ENUM.BYE,
            numseq=self.last_try_numseq,
        )
        return bye_pckt

    # Obtem pwd da linha de comando
    # Retorna None se EOF, ou um PwdGuess com os bytes da tentativa
    def get_new_guess(self):
        
        line = sys.stdin.readline()
        
        if line == "":
            return None
        
        line = line.strip()
            
        while(len(line) < self.pwd_size):
            line += " "

        pwd_guess = PwdGuess(pwd_guess_txt=line)
        
        # Se a validação da senha falhar cria diretamente dos bytes para o servidor rejeitar com ERR
        if not hasattr(pwd_guess, 'txt'):
            raw = b""
            for c in line[:8]:
                if c.isdigit():
                    raw += bytes([int(c)])
                else:
                    raw += bytes([ord(c)])
            while len(raw) < 8:
                raw += b" "
            pwd_guess = PwdGuess(pwd_guess_bytes=raw)
        
        return pwd_guess


def main():
    [_, host, port] = sys.argv
    port = int(port)

    server_addr = (host, port)

    with ClientSocket(server_addr) as client: 
        hel_pckt = client.generate_hel_pckt()
        
        # LOOP DO HEL: tenta enviar, valida a RES e registra NA e NT
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

        # LOOP DO TRY: Obtem pwd, envia pacote, obtem RES e repete quando há erro
        tries_success = 0
        while tries_success < max_tries - 1:
            pwd_guess = client.get_new_guess()
            
            if pwd_guess is None:
                break
            
            try_pckt = client.generate_try_pckt(pwd_guess)
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

            # Quanto recebe um ERR, faz o registro adequado e diminui 1 das tentativas
            if res_to_try_pckt.type == TYPE_ENUM.ERR:
                if res_to_try_pckt.numseq > 0:
                    print(f"RETRY {res_to_try_pckt.numseq}")
                    client.try_count -= 1
                else:
                    print("ERRO")
                    sys.exit()
                continue
            
            # Obtem o padrão do server e verifica se é o certo
            pattern = res_to_try_pckt.pwd_guess.txt[:client.pwd_size]
            print(f"{client.try_count}({res_to_try_pckt.numseq}) {pattern}")
            tries_success += 1

            if pattern == "*" * client.pwd_size:
                break

        bye_pckt = client.generate_bye_pckt()
        
        # LOOP DO BYE: gera pacote, recebe RES, printa a resposta certa
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
