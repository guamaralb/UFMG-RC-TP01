"""
Testes de jogo completo.

Cobre:
  - tamanho de senha (abaixo do mínimo, acima do máximo)
  - conteúdo inválido de senha (dígito repetido, chars proibidos)
  - padrões de resposta (*, +, -, ?)
  - erros de checksum (servidor deve ignorar — sem resposta)
  - erros de tipo (tipo inesperado no momento errado)
  - fluxo completo do jogo com senhas de 4 a 8 dígitos
  - fluxo com ERR: retry após senha inválida
"""

import os
import sys
import socket
import struct
import subprocess
import time
from contextlib import contextmanager

import pytest

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJ_ROOT, "rc_tp01"))

from packet import PacketClass, TYPE_ENUM
from pwd_guess import PwdGuess


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure
# ─────────────────────────────────────────────────────────────────────────────

_next_port = 21000


def alloc_port() -> int:
    global _next_port
    p = _next_port
    _next_port += 1
    return p


@contextmanager
def start_server(port: int, password: str, max_tries: int = 6):
    proc = subprocess.Popen(
        ["poetry", "run", "python3", "rc_tp01/server.py",
         str(port), password, str(max_tries)],
        cwd=PROJ_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1.2)
    try:
        yield proc
    finally:
        proc.terminate()
        proc.wait()


def run_game(port: int, password: str, max_tries: int, guesses: list[str],
             timeout: int = 15) -> str:
    srv = subprocess.Popen(
        ["poetry", "run", "python3", "rc_tp01/server.py",
         str(port), password, str(max_tries)],
        cwd=PROJ_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1.0)
    result = subprocess.run(
        ["poetry", "run", "python3", "rc_tp01/client.py", "localhost", str(port)],
        input=("\n".join(guesses) + "\n").encode(),
        capture_output=True,
        cwd=PROJ_ROOT,
        timeout=timeout,
    )
    time.sleep(0.3)
    srv.terminate()
    srv.wait()
    return result.stdout.decode()


class RawClient:
    """Cliente UDP que envia pacotes arbitrários — usado para testar o servidor diretamente."""

    def __init__(self, port: int, timeout: float = 2.0):
        self.addr = ("localhost", port)
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.soc.settimeout(timeout)

    def close(self):
        self.soc.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── envio ──

    def send(self, pckt: PacketClass):
        self.soc.sendto(pckt.bytes, self.addr)

    def send_raw(self, data: bytes):
        self.soc.sendto(data, self.addr)

    # ── recepção ──

    def recv(self) -> PacketClass:
        data, _ = self.soc.recvfrom(1024)
        return PacketClass.try_create_from_bytes(data)

    def no_response(self) -> bool:
        """True se nenhuma resposta chegar dentro do timeout."""
        try:
            self.soc.recvfrom(1024)
            return False
        except socket.timeout:
            return True

    # ── helpers de protocolo ──

    def hel(self, numseq: int = 0) -> PacketClass:
        self.send(PacketClass(type=TYPE_ENUM.HEL, numseq=numseq))
        return self.recv()

    def try_valid(self, numseq: int, pwd_txt: str, pwd_size: int = 4) -> PacketClass:
        PwdGuess.pwd_size = pwd_size
        pg = PwdGuess(pwd_guess_txt=pwd_txt)
        self.send(PacketClass(type=TYPE_ENUM.TRY, numseq=numseq, pwd_guess=pg))
        return self.recv()

    def bye(self, numseq: int) -> PacketClass:
        self.send(PacketClass(type=TYPE_ENUM.BYE, numseq=numseq))
        return self.recv()

    # ── helpers para testes de erro ──

    def try_raw_pwd(self, numseq: int, pwd_bytes: bytes) -> PacketClass:
        """Envia TRY com bytes arbitrários no campo pwd — bypassa PwdGuess."""
        padded = (pwd_bytes + b"\x20" * 8)[:8]
        raw = bytearray(struct.pack("!BBh8s", TYPE_ENUM.TRY.value, 0, numseq, padded))
        cs = 0
        for i, b in enumerate(raw):
            if i != 1:
                cs ^= b
        raw[1] = cs
        self.send_raw(bytes(raw))
        return self.recv()

    def send_with_bad_checksum(self, pckt: PacketClass):
        """Envia o pacote com o byte de checksum corrompido."""
        bad = bytearray(pckt.bytes)
        bad[1] ^= 0xFF
        self.send_raw(bytes(bad))

    def send_type_raw(self, type_val: int, numseq: int) -> PacketClass:
        """Envia pacote de 4 bytes com tipo arbitrário."""
        raw = bytearray(struct.pack("!BBh", type_val, 0, numseq))
        cs = 0
        for i, b in enumerate(raw):
            if i != 1:
                cs ^= b
        raw[1] = cs
        self.send_raw(bytes(raw))
        return self.recv()


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_pwd_size():
    PwdGuess.pwd_size = 4
    yield
    PwdGuess.pwd_size = 4


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tamanho de senha
# ─────────────────────────────────────────────────────────────────────────────

class TestTamanhoDeSenha:

    def test_tamanho_4_aceito(self):
        PwdGuess.pwd_size = 4
        pg = PwdGuess(pwd_guess_txt="1234")
        assert hasattr(pg, "txt")

    def test_tamanho_5_aceito(self):
        PwdGuess.pwd_size = 5
        pg = PwdGuess(pwd_guess_txt="12345")
        assert hasattr(pg, "txt")

    def test_tamanho_6_aceito(self):
        PwdGuess.pwd_size = 6
        pg = PwdGuess(pwd_guess_txt="123456")
        assert hasattr(pg, "txt")

    def test_tamanho_7_aceito(self):
        PwdGuess.pwd_size = 7
        pg = PwdGuess(pwd_guess_txt="1234567")
        assert hasattr(pg, "txt")

    def test_tamanho_8_aceito(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="12345678")
        assert hasattr(pg, "txt")

    def test_string_vazia_rejeitada(self):
        PwdGuess.pwd_size = 4
        pg = PwdGuess(pwd_guess_txt="")
        assert not hasattr(pg, "txt"), "String vazia deve ser rejeitada"

    def test_tamanho_9_rejeitado(self):
        """Spec: máximo de 8 dígitos."""
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="123456789")
        assert not hasattr(pg, "txt"), "9 dígitos deve ser rejeitado"

    def test_tamanho_3_abaixo_do_minimo(self):
        """Spec: mínimo de 4 dígitos."""
        PwdGuess.pwd_size = 4
        pg = PwdGuess(pwd_guess_txt="123")
        assert not hasattr(pg, "txt"), "3 dígitos deve ser rejeitado para pwd_size=4"

    def test_tamanho_1_rejeitado(self):
        PwdGuess.pwd_size = 4
        pg = PwdGuess(pwd_guess_txt="1")
        assert not hasattr(pg, "txt")

    def test_tamanho_exato_8_sem_espacos(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="98765432")
        assert hasattr(pg, "txt")
        assert pg.txt == "98765432"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Conteúdo inválido de senha
# ─────────────────────────────────────────────────────────────────────────────

class TestConteudoInvalidoDeSenha:

    def test_digito_repetido_inicio(self):
        pg = PwdGuess(pwd_guess_txt="2234")
        assert not hasattr(pg, "txt")

    def test_digito_repetido_fim(self):
        pg = PwdGuess(pwd_guess_txt="2344")
        assert not hasattr(pg, "txt")

    def test_digito_repetido_meio(self):
        pg = PwdGuess(pwd_guess_txt="2334")
        assert not hasattr(pg, "txt")

    def test_todos_digitos_iguais(self):
        pg = PwdGuess(pwd_guess_txt="1111")
        assert not hasattr(pg, "txt")

    def test_letra_maiuscula_rejeitada(self):
        pg = PwdGuess(pwd_guess_txt="12A4")
        assert not hasattr(pg, "txt")

    def test_letra_minuscula_rejeitada(self):
        pg = PwdGuess(pwd_guess_txt="12a4")
        assert not hasattr(pg, "txt")

    def test_char_especial_rejeitado(self):
        pg = PwdGuess(pwd_guess_txt="12#4")
        assert not hasattr(pg, "txt")

    def test_espaco_no_meio_rejeitado(self):
        """Espaço só é válido APÓS os dígitos da senha."""
        pg = PwdGuess(pwd_guess_txt="1 34")
        assert not hasattr(pg, "txt")

    def test_zero_valido_no_inicio(self):
        pg = PwdGuess(pwd_guess_txt="0123")
        assert hasattr(pg, "txt")
        assert pg.txt == "0123"

    def test_zero_valido_no_fim(self):
        pg = PwdGuess(pwd_guess_txt="1230")
        assert hasattr(pg, "txt")

    def test_todos_zeros_gera_aleatoria(self):
        """Spec: sequência de zeros → senha aleatória daquele tamanho."""
        pg = PwdGuess(pwd_guess_txt="0000")
        assert hasattr(pg, "txt")
        assert len(pg.txt) == 4
        assert pg.txt != "0000"
        assert len(set(pg.txt)) == 4, "Senha aleatória não deve ter dígitos repetidos"

    def test_digito_repetido_8_digitos(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="12345678")
        assert hasattr(pg, "txt")

    def test_digito_repetido_rejeitado_8_digitos(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="11345678")
        assert not hasattr(pg, "txt")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Padrões de resposta (*, +, -, ?)
# ─────────────────────────────────────────────────────────────────────────────

class TestPadroesDeResposta:

    def test_todas_estrelas(self):
        pg = PwdGuess(pwd_guess_txt="****")
        assert hasattr(pg, "txt")

    def test_todas_mais(self):
        pg = PwdGuess(pwd_guess_txt="++++")
        assert hasattr(pg, "txt")

    def test_todas_menos(self):
        pg = PwdGuess(pwd_guess_txt="----")
        assert hasattr(pg, "txt")

    def test_mix_valido(self):
        pg = PwdGuess(pwd_guess_txt="*+--")
        assert hasattr(pg, "txt")

    def test_interrogacoes_hel(self):
        """Resposta ao HEL usa '?' para indicar tamanho da senha."""
        pg = PwdGuess(pwd_guess_txt="????" + "    ")
        assert hasattr(pg, "txt")

    def test_interrogacoes_8_digitos(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="????????")
        assert hasattr(pg, "txt")

    def test_char_invalido_no_padrao(self):
        pg = PwdGuess(pwd_guess_txt="*+!-")
        assert not hasattr(pg, "txt")

    def test_letra_no_padrao_rejeitada(self):
        pg = PwdGuess(pwd_guess_txt="*+x-")
        assert not hasattr(pg, "txt")

    def test_padrao_misturado_com_digito_invalido(self):
        """Posição 0 é dígito, mas pos 1 é '*' — mistura inválida."""
        pg = PwdGuess(pwd_guess_txt="5*--")
        assert not hasattr(pg, "txt")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Erros de checksum
# ─────────────────────────────────────────────────────────────────────────────

class TestChecksum:

    def test_checksum_valido_xor_zero(self):
        """Pacote bem formado: XOR de todos os bytes deve ser 0."""
        PwdGuess.pwd_size = 4
        pg = PwdGuess(pwd_guess_txt="2345")
        pckt = PacketClass(type=TYPE_ENUM.TRY, numseq=1, pwd_guess=pg)
        xor = 0
        for b in pckt.bytes:
            xor ^= b
        assert xor == 0

    def test_checksum_valido_hel(self):
        pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        xor = 0
        for b in pckt.bytes:
            xor ^= b
        assert xor == 0

    def test_checksum_valido_bye(self):
        pckt = PacketClass(type=TYPE_ENUM.BYE, numseq=3)
        xor = 0
        for b in pckt.bytes:
            xor ^= b
        assert xor == 0

    def test_checksum_corrompido_invalido(self):
        """Após corromper o checksum, XOR não deve ser 0."""
        pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        bad = bytearray(pckt.bytes)
        bad[1] ^= 0xFF
        xor = 0
        for b in bad:
            xor ^= b
        assert xor != 0

    def test_hel_checksum_invalido_sem_resposta(self):
        """Servidor deve ignorar pacote com checksum inválido (sem resposta)."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port, timeout=1.5) as c:
                hel = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
                c.send_with_bad_checksum(hel)
                assert c.no_response(), "Servidor não deve responder a checksum inválido"

    def test_try_checksum_invalido_sem_resposta(self):
        """TRY com checksum corrompido deve ser ignorado."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()  # handshake válido
                PwdGuess.pwd_size = 4
                try_pckt = PacketClass(
                    type=TYPE_ENUM.TRY, numseq=1,
                    pwd_guess=PwdGuess(pwd_guess_txt="1234"),
                )
                c.soc.settimeout(1.5)
                c.send_with_bad_checksum(try_pckt)
                assert c.no_response()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Erros de tipo
# ─────────────────────────────────────────────────────────────────────────────

class TestErrosDeTipo:

    def test_hel_duplicado_sem_resposta(self):
        """Segundo HEL durante o jogo: servidor não reconhece tipo — sem resposta."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()  # primeiro HEL válido
                # Envia segundo HEL com numseq diferente
                c.soc.settimeout(1.5)
                hel2 = PacketClass(type=TYPE_ENUM.HEL, numseq=99)
                c.send(hel2)
                # Servidor está no loop TRY/BYE; não processa HEL → sem resposta
                assert c.no_response()

    def test_res_enviado_ao_servidor_sem_resposta(self):
        """Servidor não deve responder a pacote do tipo RES (cliente não deve enviar RES)."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()
                PwdGuess.pwd_size = 4
                res_pckt = PacketClass(
                    type=TYPE_ENUM.RES, numseq=5,
                    pwd_guess=PwdGuess(pwd_guess_txt="*-++"),
                )
                c.soc.settimeout(1.5)
                c.send(res_pckt)
                assert c.no_response()

    def test_tipo_desconhecido_sem_resposta(self):
        """Tipo de byte 99 (inexistente) não pode ser decodificado — servidor ignora."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port, timeout=1.5) as c:
                c.hel()
                # Pacote com tipo 99 — TYPE_ENUM não reconhece, try_create_from_bytes → None
                raw = bytearray(struct.pack("!BBh", 99, 0, 1))
                cs = 0
                for i, b in enumerate(raw):
                    if i != 1:
                        cs ^= b
                raw[1] = cs
                c.send_raw(bytes(raw))
                assert c.no_response()

    def test_err_enviado_ao_servidor_sem_resposta(self):
        """Servidor não deve responder a pacote ERR enviado pelo cliente."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port, timeout=1.5) as c:
                c.hel()
                err_pckt = PacketClass(type=TYPE_ENUM.ERR, numseq=1)
                c.send(err_pckt)
                assert c.no_response()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fluxo completo do jogo
# ─────────────────────────────────────────────────────────────────────────────

class TestJogoCompleto:

    def test_senha_4_digitos_acerto_primeira(self):
        out = run_game(alloc_port(), "2345", 4, ["2345"])
        assert "NA=4" in out
        assert "NT=4" in out
        assert "****" in out
        assert "Senha=2345" in out

    def test_senha_4_digitos_todas_erradas(self):
        """Chutes sem nenhum dígito presente → todos '-'."""
        out = run_game(alloc_port(), "2345", 6, ["6789", "6780", "6701"])
        assert "----" in out

    def test_senha_4_digitos_todos_posicao_errada(self):
        """Dígitos presentes mas em posição errada → todos '+'."""
        # Senha 2345, chute 3456: 3+,4+,5+,6-  → não são todos +
        # Senha 1234, chute 4321: 4-,3+,2+,1+ → não são todos +
        # Senha 1234, chute 2143: 2+,1+,4+,3+  → todos +!
        out = run_game(alloc_port(), "1234", 6, ["2143"])
        assert "++++" in out

    def test_senha_4_digitos_acerto_ultima(self):
        """Acerta na última tentativa antes do BYE."""
        out = run_game(alloc_port(), "2345", 4, ["6789", "6780", "2345"])
        assert "****" in out
        assert "Senha=2345" in out

    def test_senha_4_com_zero(self):
        out = run_game(alloc_port(), "0234", 4, ["0234"])
        assert "****" in out
        assert "Senha=0234" in out

    def test_senha_4_iniciando_zero(self):
        out = run_game(alloc_port(), "0123", 4, ["0123"])
        assert "****" in out
        assert "Senha=0123" in out

    def test_senha_5_digitos(self):
        out = run_game(alloc_port(), "13579", 6, ["13579"])
        assert "NA=5" in out
        assert "*****" in out
        assert "Senha=13579" in out

    def test_senha_6_digitos(self):
        out = run_game(alloc_port(), "024689", 6, ["024689"])
        assert "NA=6" in out
        assert "******" in out
        assert "Senha=024689" in out

    def test_senha_7_digitos(self):
        out = run_game(alloc_port(), "1357920", 8, ["1357920"])
        assert "NA=7" in out
        assert "*******" in out

    def test_senha_8_digitos(self):
        out = run_game(alloc_port(), "12345678", 8, ["12345678"])
        assert "NA=8" in out
        assert "NT=8" in out
        assert "********" in out
        assert "Senha=12345678" in out

    def test_senha_8_digitos_parcial(self):
        """Sequência com chutes parcialmente corretos antes de acertar."""
        out = run_game(alloc_port(), "12345678", 6, ["87654321", "12345678"])
        assert "12345678" in out

    def test_numseq_res_decresce(self):
        """NUMSEQ do RES deve ser NT − NUMSEQ(TRY) → vai diminuindo."""
        # Senha 2345, NT=4: TRY1→RES3, TRY2→RES2
        out = run_game(alloc_port(), "2345", 4, ["6789", "6780"])
        assert "1(3)" in out
        assert "2(2)" in out

    def test_bye_apos_tentativas_esgotadas(self):
        """Ao esgotar max_tries-1 tentativas, cliente envia BYE e recebe senha."""
        # NT=4 → 3 TRYs antes do BYE
        out = run_game(alloc_port(), "2345", 4, ["6789", "6780", "6701"])
        assert "Senha=2345" in out

    def test_formato_na_nt(self):
        out = run_game(alloc_port(), "2345", 6, ["2345"])
        assert "NA=4, NT=6" in out

    def test_formato_try_response(self):
        """Formato exato: '<numseq>(<restantes>) <padrão>'."""
        # Senha 2345, chute 2154: 2=* 1=- 5=+ 4=+ → "*-++"
        out = run_game(alloc_port(), "2345", 6, ["2154"])
        assert "1(5) *-++" in out

    def test_formato_senha_final(self):
        out = run_game(alloc_port(), "2345", 4, ["2345"])
        assert "Senha=2345" in out

    def test_acerto_interrompe_loop(self):
        """Ao acertar a senha, o cliente deve enviar BYE sem ler mais linhas."""
        # Damos mais chutes do que o necessário; se o cliente parar cedo, não usa os extras
        out = run_game(alloc_port(), "2345", 6, ["2345", "0000", "0000"])
        lines = [l for l in out.splitlines() if l.strip()]
        # Deve ter acertado na primeira tentativa e encerrado
        assert "****" in out
        # Não deve ter processado tentativas após o acerto
        assert out.count("(") == 1, "Deve haver apenas uma linha de TRY antes do BYE"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Fluxo com ERR
# ─────────────────────────────────────────────────────────────────────────────

class TestFluxoERR:

    def test_try_digito_repetido_retorna_err(self):
        """TRY com dígito repetido: servidor deve responder ERR(numseq > 0)."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()
                resp = c.try_raw_pwd(1, bytes([2, 2, 3, 4]))
                assert resp is not None
                assert resp.type == TYPE_ENUM.ERR
                assert resp.numseq == 1, "ERR deve ter NUMSEQ = numseq do TRY inválido"

    def test_try_valor_invalido_retorna_err(self):
        """Bytes > 9 e != ASCII de *, +, - são inválidos como dígitos."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()
                # Byte 15 não é dígito (0–9) nem símbolo válido quando decodificado
                resp = c.try_raw_pwd(1, bytes([2, 15, 3, 4]))
                assert resp is not None
                assert resp.type == TYPE_ENUM.ERR

    def test_err_numseq_maior_zero_retry_aceito(self):
        """Após ERR(>0), servidor aceita novo TRY com o MESMO numseq."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                c.hel()
                c.try_raw_pwd(1, bytes([2, 2, 3, 4]))  # ERR(1)
                resp = c.try_valid(1, "1234")           # retry com numseq=1
                assert resp.type == TYPE_ENUM.RES

    def test_err_sequencia_correta(self):
        """ERR não consome tentativa: numseq do RES subsequente ainda é NT-1."""
        port = alloc_port()
        with start_server(port, "2345", 4):
            with RawClient(port) as c:
                res_hel = c.hel()
                nt = res_hel.numseq  # = 4
                c.try_raw_pwd(1, bytes([2, 2, 3, 4]))  # inválido → ERR(1), não consome
                res = c.try_valid(1, "1234")           # válido, numseq=1
                assert res.type == TYPE_ENUM.RES
                assert res.numseq == nt - 1            # 3 = 4 - 1

    def test_multiplos_err_depois_acerta(self):
        """Múltiplos erros de conteúdo seguidos de TRY válido."""
        port = alloc_port()
        with start_server(port, "2345", 6):
            with RawClient(port) as c:
                c.hel()
                c.try_raw_pwd(1, bytes([1, 1, 1, 1]))  # ERR
                c.try_raw_pwd(1, bytes([2, 2, 2, 2]))  # ERR
                resp = c.try_valid(1, "2345")           # acerto
                assert resp.type == TYPE_ENUM.RES
                assert resp.pwd_guess.txt[:4] == "****"

    def test_err_numseq_zero_numseq_errado(self):
        """TRY com numseq errado (fora de ordem) → ERR com NUMSEQ=0."""
        port = alloc_port()
        with start_server(port, "2345", 6):
            with RawClient(port) as c:
                c.hel()
                resp = c.try_valid(5, "1234")  # esperado numseq=1, recebido 5
                assert resp.type == TYPE_ENUM.ERR
                assert resp.numseq == 0

    def test_err_integracao_retry_via_cliente(self):
        """Fluxo completo via subprocess: RETRY impresso, jogo prossegue."""
        # O cliente normal valida a senha antes de enviar, então não consegue
        # forçar um ERR via stdin. Este teste verifica que o jogo termina
        # normalmente sem ERR em condições de input válido.
        out = run_game(alloc_port(), "2345", 6, ["1234", "2345"])
        assert "Senha=2345" in out
