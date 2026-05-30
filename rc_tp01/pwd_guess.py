from random import randrange
import struct

class PwdGuess():
    pwd_size = 0
    
    def __init__(self, pwd_guess_txt: str = None, pwd_guess_bytes: bytes = None):
        #print("~", pwd_guess_txt, pwd_guess_bytes)
            if isinstance(pwd_guess_txt, str):

                if self._check_is_all_zeros(pwd_guess_txt):
                    pwd_guess_txt = self._create_random_pwd()

                self.txt = pwd_guess_txt
                self.bytes = self._encode_pwd()

            elif isinstance(pwd_guess_bytes, bytes):
                self.bytes = pwd_guess_bytes
                self.txt = self._decode_pwd()

            else:
                print("PWDGUESS: Error de nenhum valor informado no tipo correto")            

    def is_valid(self):
        return self._validate_pwd_guess(self.txt)
    
    
    def _validate_pwd_guess(self, txt):
        if not self._has_right_size(txt):
            #print("~A")
            return False

        if not self._check_valid_chars(txt):
            #print("~B")
            return False

        if self._check_repeated_chars(txt):
            #print("~C")
            return False

        return True
        

    def _has_right_size(self, txt: str):
        if len(txt) == 0 or len(txt) > 8:
            return False

        frist = txt[0]

        if frist == "?":
            return True

        if frist in "+-*":
            beg = txt[:self.pwd_size]
            end = txt[self.pwd_size:]

            for c in beg:
                if c not in "+-*":
                    return False

            for c in end:
                if c != "0" and c != " ":
                    return False

            return True

        if frist.isdigit():
            beg = txt[:self.pwd_size]
            end = txt[self.pwd_size:]

            for c in beg:
                if not c.isdigit():
                    return False

            for c in end:
                if c != "0" and c != " ":
                    return False

            return True

        return False


    def _check_is_all_zeros(self, txt):
        if len(txt) != self.pwd_size:
            return False

        for i in range(len(txt)):
            if txt[i] != "0":
                return False

        return True
        
        
    def _check_valid_chars(self, txt):
        for c in txt:
            if c not in "0123456789 ?*+-":
                return False
        
        return True



    def _check_repeated_chars(self, txt):
        for i in range(self.pwd_size):
            if txt[i].isdigit():
                for j in range(len(txt)):
                    if i != j and txt[i] == txt[j]:
                        return True
        return False
    
    
    def _create_random_pwd(self):
        size = self.pwd_size

        min = int("1" + "0" * (size - 1))
        max = int("9" * size)

        pwd_txt = str(randrange(min, max, 1))

        while len(pwd_txt) < size:
            pwd_txt = "0" + pwd_txt

        if not self._validate_pwd_guess(pwd_txt):
            return self._create_random_pwd()

        return pwd_txt
    
    def _encode_pwd(self):
        result = b''

        for c in self.txt:
            if c.isdigit():
                result += bytes([int(c)])
            else:
                result += bytes([ord(c)])

        return result


    def _decode_pwd(self):
        txt = ''

        for b in self.bytes:
            if 0 <= b <= 9:
                txt += str(b)
            else:
                txt += chr(b)

        return txt