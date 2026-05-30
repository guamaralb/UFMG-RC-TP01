# GUSTAVO AMARAL BERNARDINO

from random import randrange

class PwdGuess():
    pwd_size = 0
    
    # Permite a inicialização de pwd com bytes ou txt
    def __init__(self, pwd_guess_txt: str = None, pwd_guess_bytes: bytes = None):
        if pwd_guess_txt is not None:
            if self._check_is_all_zeros(pwd_guess_txt):
                pwd_guess_txt = self._create_random_pwd()

            if self.is_valid(pwd_guess_txt):
                self.txt = pwd_guess_txt

                # Depois de confirmar que o pwd txt é valido, gera o pwd em bytes
                pwd_bytes = b""

                for char in self.txt:
                    if char.isdigit():
                        value = int(char)
                    else:
                        value = ord(char)

                    pwd_bytes += bytes([value])

                while len(pwd_bytes) < 8:
                    pwd_bytes += b" "

                self.bytes = pwd_bytes

        elif pwd_guess_bytes is not None:
            self.bytes = pwd_guess_bytes

            # Gera o pwd em txt com base nos bytes
            pwd_txt = ""

            for value in self.bytes:
                if value >= 0 and value <= 9:
                    pwd_txt += str(value)
                else:
                    pwd_txt += chr(value)

            self.txt = pwd_txt   
    
    # Valida o texto da pwd com base nas regras
    def is_valid(self, txt = None):
        if txt is None:
            txt = self.txt

        # Validação de tamanho
        if len(txt) == 0 or len(txt) > 8:
            return False

        # Validação de caracteres permitidos
        for c in txt:
            if c not in "0123456789 ?*+-":
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

        elif frist.isdigit():
            beg = txt[:self.pwd_size]
            end = txt[self.pwd_size:]

            if len(beg) < self.pwd_size:
                return False

            for c in beg:
                if not c.isdigit():
                    return False

            for c in end:
                if c != "0" and c != " ":
                    return False

        else:
            return False

        # Validação de não-repetição de caracteres, quando números
        for i in range(self.pwd_size):
            if txt[i].isdigit():
                for j in range(len(txt)):
                    if i != j and txt[i] == txt[j]:
                        return False

        return True        


    def _check_is_all_zeros(self, txt):
        if len(txt) != self.pwd_size:
            return False

        for i in range(len(txt)):
            if txt[i] != "0":
                return False

        return True
        

    def _create_random_pwd(self):
        size = self.pwd_size

        min = int("1" + "0" * (size - 1))
        max = int("9" * size)

        pwd_txt = str(randrange(min, max, 1))

        while len(pwd_txt) < size:
            pwd_txt = "0" + pwd_txt

        if not self.is_valid(pwd_txt):
            return self._create_random_pwd()

        return pwd_txt