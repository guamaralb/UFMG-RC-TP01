from random import randrange

class PwdGuess():
    pwd_size = 0
    
    def __init__(self, pwd_guess_txt: str = None, pwd_guess_bytes: bytes = None, is_hel=False):
        self.is_hel = is_hel
        print("PWDGUESS: ", pwd_guess_txt, pwd_guess_bytes)        
        if isinstance(pwd_guess_txt, str):
            
            if self._check_is_all_zeros(pwd_guess_txt):
                pwd_guess_txt = self._create_random_pwd()
                
            if self._validate_pwd_guess(pwd_guess_txt):
                self.txt = pwd_guess_txt
                self.bytes = pwd_guess_txt.encode()
                
            else:
                print("PWDGUESS: Error de senha invalida quando txt")
        
        elif isinstance(pwd_guess_bytes, bytes):
            self.bytes = pwd_guess_bytes
            self.txt = pwd_guess_bytes.decode()
            
            if not self._validate_pwd_guess(self.txt):
                print("PWDGUESS: Error de senha invalida quando bytes")

        else:
            print("PWDGUESS: Error de nenhum valor informado no tipo correto")


    def _validate_pwd_guess(self, txt):
        if self.is_hel and txt == " " * 8:
            return True

        if self._check_size(txt):
            print("ERRO NA VALIDAÇÃO DA SENHA: B")
            return False

        if not self._check_valid_chars(txt):
            print("ERRO NA VALIDAÇÃO DA SENHA: C")
            return False

        if self._check_repeated_chars(txt):
            print("ERRO NA VALIDAÇÃO DA SENHA: D")
            return False

        return True
        

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


    def _check_size(self, txt):
        spaces = 0
        
        for c in txt:
            if c == " ":
                spaces += 1
            
        if self.pwd_size + spaces == 8:
            True
        else:
            False


    def _check_repeated_chars(self, txt):
        for i in range(len(txt)):
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
    