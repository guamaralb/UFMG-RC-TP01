from enum import Enum
import struct
from pwd_guess import PwdGuess

STRUCT_CODE = "!BBH8s"

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
        seqnum: int=None,
        pwd_guess: PwdGuess=None,
        pckt_bytes: bytes=None
    ):
        if pckt_bytes is None:
            if isinstance(type, TYPE_ENUM):
                self.type = type
            else:
                ...
                
            if isinstance(seqnum, int):
                self.seqnum = int(seqnum)
            else:
                ...
                
            if isinstance(pwd_guess, PwdGuess):
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
    
    def _calculate_checksum(self):
        partial_checksum = 0
        
        for b in self.pwd_guess.txt.encode():
            partial_checksum ^= b
        
        
        ns_bytes = struct.pack("!H", self.seqnum)
        ns_high = ns_bytes[0]
        ns_low = ns_bytes[1]
        
        bytes = [
            self.type.value,
            ns_high,
            ns_low,
            partial_checksum
        ]
        
        final_checksum = 0
        
        for b in bytes:
            final_checksum ^= b
            
        return final_checksum
    
    def _unpack(self, pckt_bytes):
        type_value, self.checksum, self.seqnum, pwd_guess_bytes = struct.unpack(STRUCT_CODE, pckt_bytes)
        
        self.type = TYPE_ENUM(type_value)
        self.pwd_guess = PwdGuess(pwd_guess_bytes=pwd_guess_bytes)
        self.bytes = pckt_bytes
            
    def _pack(self):      
        pckt_bytes = struct.pack(
            STRUCT_CODE,
            self.type.value,
            self.checksum,
            self.seqnum,
            self.pwd_guess.bytes
        )
        
        return pckt_bytes
    
    
    def txt(self):
        return(
            f"{str(self.type.name)} | "
            f"{str(self.checksum)} | "
            f"{str(self.seqnum)} | "
            f"{str(self.pwd_guess.bytes)} | "
        )

        