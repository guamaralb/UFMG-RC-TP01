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


class PacketClass():
    def __init__(
        self,
        type: bytes=None,
        checksum: bytes=None,
        numseq: int=None,
        pwd_guess: PwdGuess=None,
        pckt_bytes: bytes=None,
    ):        
        if pckt_bytes is None:
            if type is not None:
                self.type = type
            else:
                ...
                
            if numseq is not None:
                self.numseq = int(numseq)
            else:
                ...
                
            if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
                if pwd_guess is not None:
                    self.pwd_guess = pwd_guess
                else:
                    ...
                    
            if checksum is None:
                self.checksum = self._calculate_checksum()
            else:
                self.checksum = checksum
                
            self.bytes = self._pack()
        
        else:           
            self._unpack(pckt_bytes)
    
    def is_valid(self):
        if not self.pwd_guess.is_valid():
            return False, 9
        if not self._protocol_is_valid():
            return False, 0
        else:
            return True, None
        
    def _calculate_checksum(self):
        
        numseq_bytes = struct.pack("!h", self.numseq)
        numseq_high = numseq_bytes[0]
        numseq_low = numseq_bytes[1]
        
        bytes = [
            self.type.value,
            numseq_high,
            numseq_low,
        ]
        
        if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
            pwd_guess_checksum = 0
            
            for b in self.pwd_guess.txt.encode():
                pwd_guess_checksum ^= b
            
            bytes.append(self.pwd_guess_checksum)

        checksum = 0
        
        for b in bytes:
            checksum ^= b
            
        return checksum
    
    def _unpack(self, pckt_bytes):
        ##print("~PACKET unpacking")
        type_byte = pckt_bytes[:1]
        type_value = int.from_bytes(type_byte)
        
        type = TYPE_ENUM(type_value)
        
        struct_code = ''
        
        if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
            type_value, self.checksum, self.numseq, pwd_guess_bytes = struct.unpack(STRUCT_CODE_12, pckt_bytes)
            self.pwd_guess = PwdGuess(pwd_guess_bytes=pwd_guess_bytes)
        else:
            type_value, self.checksum, self.numseq = struct.unpack(STRUCT_CODE_4, pckt_bytes)

        
        self.type = TYPE_ENUM(type_value)
        self.bytes = pckt_bytes
            
    def _pack(self):      
        ##print("~PACKET packing")
        struct_code = ''
        
        elements = [
            self.type.value,
            self.checksum,
            self.numseq,
        ]
        
        if self.type == TYPE_ENUM.TRY or self.type == TYPE_ENUM.RES:
            struct_code = STRUCT_CODE_12
            elements.append(self.pwd_guess.bytes)
        else:
            struct_code = STRUCT_CODE_4

        pckt_bytes = struct.pack(
            struct_code,
            *elements
        )
        
        return pckt_bytes
    
    
    def txt(self):
        if self.type == TYPE_ENUM.TRY or self.type == TYPE_ENUM.RES:
            return(
                f"{str(self.type.name)} | "
                f"{str(self.checksum)} | "
                f"{str(self.numseq)} | "
                f"{str(self.pwd_guess.bytes)} | "
            )
        else:
            return(
                f"{str(self.type.name)} | "
                f"{str(self.checksum)} | "
                f"{str(self.numseq)}"
            )

        