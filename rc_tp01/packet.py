from enum import Enum
import struct
from pwd_guess import PwdGuess

STRUCT_CODE_12 = "!BBh8s"
STRUCT_CODE_8 = "!BB"

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
        pckt_bytes: bytes=None,
    ):        
        if pckt_bytes is None:
            if type is not None:
                self.type = type
            else:
                ...
                
            if seqnum is not None:
                self.seqnum = int(seqnum)
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
    
    def _calculate_checksum(self):
        
        seqnum_bytes = struct.pack("!h", self.seqnum)
        seqnum_high = seqnum_bytes[0]
        seqnum_low = seqnum_bytes[1]
        
        bytes = [
            self.type.value,
            seqnum_high,
            seqnum_low,
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
        print("PACKET unpacking")
        struct_code = ''
        
        if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
            struct_code = STRUCT_CODE_12
        else:
            struct_code = STRUCT_CODE_8

        type_value, self.checksum, self.seqnum, pwd_guess_bytes = struct.unpack(struct_code, pckt_bytes)
        
        self.type = TYPE_ENUM(type_value)
        is_hel = (self.type == TYPE_ENUM.HEL)
        self.pwd_guess = PwdGuess(pwd_guess_bytes=pwd_guess_bytes, is_hel=is_hel)
        self.bytes = pckt_bytes
            
    def _pack(self):      
        print("PACKET packing")
        struct_code = ''
        
        if type == TYPE_ENUM.TRY or type == TYPE_ENUM.RES:
            struct_code = STRUCT_CODE_12
        else:
            struct_code = STRUCT_CODE_8

        pckt_bytes = struct.pack(
            struct_code,
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

        