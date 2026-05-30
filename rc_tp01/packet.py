# GUSTAVO AMARAL BERNARDINO

from enum import Enum
import struct
from pwd_guess import PwdGuess

STRUCT_CODE_12 = "!BBh8s"
STRUCT_CODE_4 = "!BBh"

class TYPE_ENUM(Enum):
    HEL = 1
    TRY = 2
    RES = 3
    BYE = 4
    ERR = 5

# Classe que representa o pacote enviado nas comunicações dos sockets
# Pode ser instanciada a partir dos bytes ou dos atributos
class PacketClass():
    def __init__(
        self,
        type: TYPE_ENUM= None,
        numseq: int=None,
        pwd_guess: PwdGuess=None,
        pckt_bytes: bytes=None,
    ):
        # Se não tem bytes, deve ser criada com os atributos
        if pckt_bytes is None:
            self.type = type
            self.numseq = int(numseq)
            if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
                self.pwd_guess = pwd_guess
            self.bytes = self._calculate_checksum_and_pack()
        else:
            
            # Se tem bytes, eles são unpacked para obter os atributos
            self._unpack(pckt_bytes)

    # Método para permitir que se tente criar os pckts com os bytes, o
    # que pode falhar devido a falhas da comunicação
    @classmethod
    def try_create_from_bytes(cls, pckt_bytes: bytes):
        try:
            return cls(pckt_bytes=pckt_bytes)
        except Exception:
            return None

    # Método que verifica o pwd e o protocolo, retornando o status da
    # verificação e o seqnum correspondente ao tipo de erro
    def is_valid(self, numseq: int, max_tries: int = None):
        if not self._checksum_is_valid():
            return False, None
        return self._protocol_is_valid(numseq, max_tries)

    def _protocol_is_valid(self, numseq: int, max_tries: int = None):
        if self.numseq != numseq:
            return False, 0
        if self.type == TYPE_ENUM.TRY:
            if max_tries is not None and self.numseq > max_tries:
                return False, 0
            if not self.pwd_guess.is_valid():
                return False, self.numseq  # ERR NUMSEQ > 0: senha inválida, pode tentar de novo
        return True, None

    def _checksum_is_valid(self):
        result = 0
        for b in self.bytes:
            result ^= b
        return result == 0

    # Método que desempacota os bytes, que varia de acordo com o tipo de MSG
    def _unpack(self, pckt_bytes: bytes):
        type_value = int.from_bytes(pckt_bytes[:1])
        pckt_type = TYPE_ENUM(type_value)

        if pckt_type == TYPE_ENUM.TRY or pckt_type == TYPE_ENUM.RES:
            type_value, self.checksum, self.numseq, pwd_guess_bytes = struct.unpack(STRUCT_CODE_12, pckt_bytes)
            self.pwd_guess = PwdGuess(pwd_guess_bytes=pwd_guess_bytes)
        else:
            type_value, self.checksum, self.numseq = struct.unpack(STRUCT_CODE_4, pckt_bytes)

        self.type = TYPE_ENUM(type_value)
        self.bytes = pckt_bytes

    # Método que empacota e gera a checksum ao mesmo tempo
    def _calculate_checksum_and_pack(self):
        elements = [
            self.type.value,
            0,
            self.numseq,]
        

        if self.type == TYPE_ENUM.TRY or self.type == TYPE_ENUM.RES:
            struct_code = STRUCT_CODE_12
            elements.append(self.pwd_guess.bytes)
        else:
            struct_code = STRUCT_CODE_4

        pckg_bytes = bytearray(struct.pack(struct_code, *elements))

        checksum = 0
        for i, b in enumerate(pckg_bytes):
            if i != 1:
                checksum ^= b
        pckg_bytes[1] = checksum
        self.checksum = checksum

        return pckg_bytes