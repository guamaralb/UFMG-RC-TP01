import sys
import os
import socket
import subprocess
import time
import pytest

PROJ_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJ_ROOT, 'rc_tp01'))

from pwd_guess import PwdGuess
from packet import PacketClass, TYPE_ENUM
from server import ServerSocket


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(autouse=True)
def reset_pwd_size():
    PwdGuess.pwd_size = 4
    yield
    PwdGuess.pwd_size = 0


@pytest.fixture
def server_4():
    PwdGuess.pwd_size = 4
    return ServerSocket(pwd_answer_txt="2345", max_tries="4")


# ============================================================
# PwdGuess — validação
# ============================================================

class TestPwdGuessValidacao:

    def test_senha_valida_4_digitos(self):
        pg = PwdGuess(pwd_guess_txt="2345")
        assert hasattr(pg, 'txt')
        assert pg.txt == "2345"

    def test_senha_valida_8_digitos(self):
        PwdGuess.pwd_size = 8
        pg = PwdGuess(pwd_guess_txt="12345678")
        assert hasattr(pg, 'txt')
        assert pg.txt == "12345678"

    def test_digito_repetido_rejeitado(self):
        pg = PwdGuess(pwd_guess_txt="2234")
        assert not hasattr(pg, 'txt'), "Senha com dígito repetido deve ser rejeitada"

    def test_caracter_invalido_rejeitado(self):
        pg = PwdGuess(pwd_guess_txt="12a4")
        assert not hasattr(pg, 'txt'), "Senha com caracter inválido deve ser rejeitada"

    def test_todos_zeros_gera_senha_aleatoria(self):
        pg = PwdGuess(pwd_guess_txt="0000")
        assert hasattr(pg, 'txt')
        assert len(pg.txt) == 4
        assert pg.txt != "0000"
        assert all(c.isdigit() for c in pg.txt)

    def test_todos_zeros_sem_repeticao(self):
        """Senha aleatória gerada a partir de zeros não deve ter dígitos repetidos."""
        for _ in range(20):
            pg = PwdGuess(pwd_guess_txt="0000")
            assert len(set(pg.txt)) == 4, "Senha aleatória tem dígitos repetidos"

    def test_simbolos_resposta_sao_validos(self):
        """Padrões de resposta do servidor (*,+,-) devem ser aceitos."""
        pg = PwdGuess(pwd_guess_txt="*+-*")
        assert hasattr(pg, 'txt')

    def test_interrogacoes_para_hel(self):
        """Padrão de resposta ao HEL (????    ) deve ser aceito."""
        pg = PwdGuess(pwd_guess_txt="????" + "    ")
        assert hasattr(pg, 'txt')


# ============================================================
# PwdGuess — encoding/decoding
# ============================================================

class TestPwdGuessEncoding:

    def test_digito_encodado_como_inteiro(self):
        """Dígito '2' deve virar byte 0x02, não ASCII 0x32."""
        pg = PwdGuess(pwd_guess_txt="2345")
        assert pg.bytes[0] == 2
        assert pg.bytes[1] == 3
        assert pg.bytes[2] == 4
        assert pg.bytes[3] == 5

    def test_simbolos_encodados_como_ascii(self):
        """'*', '+', '-' devem ser encodados como seus valores ASCII."""
        pg = PwdGuess(pwd_guess_txt="*+-*")
        assert pg.bytes[0] == ord('*')
        assert pg.bytes[1] == ord('+')
        assert pg.bytes[2] == ord('-')
        assert pg.bytes[3] == ord('*')

    def test_decode_bytes_inteiros_para_digitos(self):
        """Bytes [2,3,4,5,] devem decodificar para '2345'."""
        raw = bytes([2, 3, 4, 5, 32, 32, 32, 32])
        pg = PwdGuess(pwd_guess_bytes=raw)
        assert pg.txt[:4] == "2345"

    def test_decode_bytes_ascii_para_simbolos(self):
        """Bytes ASCII de '*','+','-','*' devem decodificar corretamente."""
        raw = bytes([ord('*'), ord('+'), ord('-'), ord('*'), 32, 32, 32, 32])
        pg = PwdGuess(pwd_guess_bytes=raw)
        assert pg.txt[:4] == "*+-*"

    def test_roundtrip_txt_para_bytes_para_txt(self):
        """Encode seguido de decode deve preservar o texto original."""
        pg1 = PwdGuess(pwd_guess_txt="2345")
        pg2 = PwdGuess(pwd_guess_bytes=pg1.bytes)
        assert pg2.txt[:4] == "2345"


# ============================================================
# PacketClass — tamanho e estrutura
# ============================================================

class TestPacketTamanho:

    def test_hel_tem_4_bytes(self):
        """HEL deve ter 4 bytes (sem campo de senha)."""
        pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        assert len(pckt.bytes) == 4

    def test_bye_tem_4_bytes(self):
        """BYE deve ter 4 bytes (sem campo de senha)."""
        pckt = PacketClass(type=TYPE_ENUM.BYE, numseq=3)
        assert len(pckt.bytes) == 4

    def test_err_tem_4_bytes(self):
        """ERR deve ter 4 bytes."""
        pckt = PacketClass(type=TYPE_ENUM.ERR, numseq=0)
        assert len(pckt.bytes) == 4

    def test_try_tem_12_bytes(self):
        """TRY deve ter 12 bytes."""
        pg = PwdGuess(pwd_guess_txt="2345")
        pckt = PacketClass(type=TYPE_ENUM.TRY, numseq=1, pwd_guess=pg)
        assert len(pckt.bytes) == 12

    def test_res_tem_12_bytes(self):
        """RES deve ter 12 bytes."""
        pg = PwdGuess(pwd_guess_txt="*-++")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=3, pwd_guess=pg)
        assert len(pckt.bytes) == 12

    def test_valores_enum_tipo(self):
        """Valores numéricos dos tipos devem seguir a spec: HEL=1..ERR=5."""
        assert TYPE_ENUM.HEL.value == 1
        assert TYPE_ENUM.TRY.value == 2
        assert TYPE_ENUM.RES.value == 3
        assert TYPE_ENUM.BYE.value == 4
        assert TYPE_ENUM.ERR.value == 5


# ============================================================
# PacketClass — numseq
# ============================================================

class TestPacketNumseq:

    def test_hel_numseq_zero(self):
        pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        assert pckt.numseq == 0

    def test_res_to_hel_numseq_igual_nt(self):
        pg = PwdGuess(pwd_guess_txt="????" + "    ")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=6, pwd_guess=pg)
        assert pckt.numseq == 6

    def test_res_to_try_numseq_igual_nt_menos_try(self):
        """NUMSEQ do RES = NT - NUMSEQ(TRY). Ex: NT=4, TRY=1 → RES=3."""
        pg = PwdGuess(pwd_guess_txt="*-++")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=3, pwd_guess=pg)
        assert pckt.numseq == 3

    def test_res_to_bye_numseq_menos_um(self):
        """RES ao BYE deve ter NUMSEQ = -1."""
        pg = PwdGuess(pwd_guess_txt="2345")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=-1, pwd_guess=pg)
        assert pckt.numseq == -1


# ============================================================
# PacketClass — pack/unpack (roundtrip)
# ============================================================

class TestPacketRoundtrip:

    def test_hel_roundtrip(self):
        pckt = PacketClass(type=TYPE_ENUM.HEL, numseq=0)
        pckt2 = PacketClass(pckt_bytes=pckt.bytes)
        assert pckt2.type == TYPE_ENUM.HEL
        assert pckt2.numseq == 0

    def test_bye_roundtrip(self):
        pckt = PacketClass(type=TYPE_ENUM.BYE, numseq=3)
        pckt2 = PacketClass(pckt_bytes=pckt.bytes)
        assert pckt2.type == TYPE_ENUM.BYE
        assert pckt2.numseq == 3

    def test_try_roundtrip(self):
        pg = PwdGuess(pwd_guess_txt="2345")
        pckt = PacketClass(type=TYPE_ENUM.TRY, numseq=1, pwd_guess=pg)
        pckt2 = PacketClass(pckt_bytes=pckt.bytes)
        assert pckt2.type == TYPE_ENUM.TRY
        assert pckt2.numseq == 1
        assert pckt2.pwd_guess.txt[:4] == "2345"

    def test_res_roundtrip(self):
        pg = PwdGuess(pwd_guess_txt="*-++")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=3, pwd_guess=pg)
        pckt2 = PacketClass(pckt_bytes=pckt.bytes)
        assert pckt2.type == TYPE_ENUM.RES
        assert pckt2.numseq == 3
        assert pckt2.pwd_guess.txt[:4] == "*-++"

    def test_res_numseq_negativo_roundtrip(self):
        """numseq = -1 deve sobreviver ao pack/unpack."""
        pg = PwdGuess(pwd_guess_txt="2345")
        pckt = PacketClass(type=TYPE_ENUM.RES, numseq=-1, pwd_guess=pg)
        pckt2 = PacketClass(pckt_bytes=pckt.bytes)
        assert pckt2.numseq == -1


# ============================================================
# Lógica do jogo — geração de resposta
# ============================================================

class TestLogicaJogo:

    def test_posicao_correta_retorna_estrela(self, server_4):
        """Dígito na posição certa → '*'."""
        pg = PwdGuess(pwd_guess_txt="2987")  # '2' correto em pos0
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer[0] == '*'

    def test_posicao_errada_retorna_mais(self, server_4):
        """Dígito presente mas em posição errada → '+'."""
        pg = PwdGuess(pwd_guess_txt="3256")  # '3' de "2345" em pos errada
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer[0] == '+'

    def test_ausente_retorna_menos(self, server_4):
        """Dígito não presente na senha → '-'."""
        pg = PwdGuess(pwd_guess_txt="1678")  # nenhum de 1,6,7,8 está em "2345"
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer == "----"

    def test_senha_correta_retorna_quatro_estrelas(self, server_4):
        """Senha completamente correta → '****'."""
        pg = PwdGuess(pwd_guess_txt="2345")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer == "****"

    def test_caso_concreto_2154(self, server_4):
        """'2154' contra '2345' → '*-++'."""
        pg = PwdGuess(pwd_guess_txt="2154")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer == "*-++"

    def test_caso_concreto_2495(self, server_4):
        """'2495' contra '2345' → '*+-*'."""
        pg = PwdGuess(pwd_guess_txt="2495")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer == "*+-*"

    def test_caso_concreto_2745(self, server_4):
        """'2745' contra '2345' → '*-**'."""
        pg = PwdGuess(pwd_guess_txt="2745")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert answer == "*-**"

    def test_resposta_tem_tamanho_correto(self, server_4):
        pg = PwdGuess(pwd_guess_txt="2154")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert len(answer) == 4

    def test_resposta_contem_apenas_simbolos_validos(self, server_4):
        pg = PwdGuess(pwd_guess_txt="2154")
        answer = server_4._generate_pattern_to_pwd_guess(pg)
        assert all(c in "*+-" for c in answer)


# ============================================================
# Integração — fluxo completo
# ============================================================

def run_game(password, max_tries, guesses, port=15555, timeout=15):
    """Inicia servidor, roda cliente com os inputs dados e retorna os outputs."""
    server_proc = subprocess.Popen(
        ["poetry", "run", "python3", "rc_tp01/server.py", str(port), password, str(max_tries)],
        cwd=PROJ_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1.5)

    stdin_data = "\n".join(guesses) + "\n"
    client_proc = subprocess.run(
        ["poetry", "run", "python3", "rc_tp01/client.py", "localhost", str(port)],
        input=stdin_data.encode(),
        capture_output=True,
        cwd=PROJ_ROOT,
        timeout=timeout,
    )

    time.sleep(0.5)
    server_proc.terminate()
    server_out = server_proc.stdout.read().decode()

    return server_out, client_proc.stdout.decode(), client_proc.stderr.decode()


class TestIntegracao:

    def test_formato_na_nt(self):
        """Saída deve conter 'NA=4, NT=4' após RES ao HEL."""
        server_out, client_out, _ = run_game("2345", 4, ["2154", "2495", "2745", "2345"])
        combined = client_out + server_out
        assert "NA=4" in combined
        assert "NT=4" in combined

    def test_formato_try_response(self):
        """Saída deve conter '1(3) *-++' para o primeiro TRY."""
        server_out, client_out, _ = run_game("2345", 4, ["2154", "2495", "2745", "2345"])
        combined = client_out + server_out
        assert "1(3) *-++" in combined

    def test_formato_senha_final(self):
        """Saída deve conter 'Senha=2345' após RES ao BYE."""
        server_out, client_out, _ = run_game("2345", 4, ["2154", "2495", "2745", "2345"])
        combined = client_out + server_out
        assert "Senha=2345" in combined

    def test_sequencia_completa(self):
        """Jogo completo deve produzir todas as respostas esperadas."""
        server_out, client_out, _ = run_game("2345", 4, ["2154", "2495", "2745", "2345"])
        combined = client_out + server_out
        assert "*-++" in combined
        assert "*+-*" in combined
        assert "*-**" in combined
        assert "Senha=2345" in combined

    def test_no_res_sem_servidor(self):
        """Cliente deve imprimir 'NO RES' ou 'CONNECTION REFUSED' sem servidor."""
        result = subprocess.run(
            ["poetry", "run", "python3", "rc_tp01/client.py", "localhost", "19999"],
            input=b"2154\n",
            capture_output=True,
            cwd=PROJ_ROOT,
            timeout=10,
        )
        output = result.stdout.decode() + result.stderr.decode()
        assert "NO RES" in output or "CONNECTION REFUSED" in output

    def test_cliente_termina_apos_no_res(self):
        """Cliente deve terminar em até 8s após NO RES (3 tentativas × 1s + overhead)."""
        start = time.time()
        subprocess.run(
            ["poetry", "run", "python3", "rc_tp01/client.py", "localhost", "19998"],
            input=b"2154\n",
            capture_output=True,
            cwd=PROJ_ROOT,
            timeout=10,
        )
        elapsed = time.time() - start
        assert elapsed < 8, f"Cliente demorou {elapsed:.1f}s para terminar após NO RES"

    def test_senha_correta_detectada(self):
        """Quando senha é acertada antes do limite, jogo deve encerrar."""
        server_out, client_out, _ = run_game("2345", 4, ["2345", "0000", "0000", "0000"])
        combined = client_out + server_out
        assert "****" in combined
