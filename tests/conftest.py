from pathlib import Path

import pytest

from engine.simulacao import Simulacao
from io_utils.carregador import carregar_regiao


@pytest.fixture
def caminho_mapa():
    return Path(__file__).resolve().parents[1] / "data" / "mapa_regiao.txt"


@pytest.fixture
def regiao(caminho_mapa):
    return carregar_regiao(str(caminho_mapa), seed_extra=101)


@pytest.fixture
def simulacao(regiao):
    return Simulacao(regiao, seed=2026)


@pytest.fixture
def jogador(simulacao):
    return simulacao.criar_jogador("Ash", aceitar_tres_iniciais=True)
