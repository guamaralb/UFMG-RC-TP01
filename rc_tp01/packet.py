from enum import Enum
import struct

STRUCT_CODE = "!BBHBBBBBBBB"

class MSG_TYPE(Enum):
    HEL = 1
    TRY = 2
    RES = 3
    BYE = 4
    ERR = 5


class Packet():
    def __init__(self, type, ns, pwd_guess):
        
        if type is MSG_TYPE:
            self.type = type
        else:
            ...
            
        if ns is int:
            self.ns = ns
            
        if pwd_guess is str:
            self.pwd_guess = pwd_guess
            
        self.check = 0
       
        
    def __init__(self, pckg_bytes):
        self._unpack(pckg_bytes)
            
    
    def pack(self):
        pckg_bytes = struct.pack(
            STRUCT_CODE,
            self.type,
            self.check,
            self.a1,
            self.a2,
            self.a3,
            self.a4,
            self.a5,
            self.a6,
            self.a7,
            self.a8
        )
        
        self.bytes = pckg_bytes
    
    
    def _unpack(self):
        self.type,
        self.check,
        self.ns,
        self.a1,
        self.a2,
        self.a3,
        self.a4,
        self.a5,
        self.a6,
        self.a7,
        self.a8 = struct.unpack(STRUCT_CODE, self.pckg_bytes)
        