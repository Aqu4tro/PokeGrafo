"""
models/especie.py
==================
Define as espécies de pokémon, suas cadeias de evolução e a tabela de
vantagens de tipo (implementação extra / bônus do enunciado).

Uma "espécie" descreve os dados que são iguais para todo pokémon daquela
espécie/fase (nome, tipos, fase de evolução, XP necessário para evoluir e
para qual espécie evolui). Um objeto `Pokemon` (em models/pokemon.py)
referencia uma `Especie` e guarda o estado individual (HP, XP, AP, DP
atuais etc).
"""

from __future__ import annotations
from typing import List, Optional, Dict


class Especie:
    """Uma fase de evolução de uma espécie de pokémon."""

    def __init__(self, id_especie: str, nome: str, tipos: List[str],
                 fase: int, xp_para_evoluir: Optional[int] = 1000,
                 evolui_para: Optional[str] = None):
        self.id = id_especie
        self.nome = nome
        self.tipos = tipos  # lista de strings, ex.: ["agua"], ["fogo","voador"]
        self.fase = fase  # 1, 2 ou 3 (no máximo 3 fases, conforme o enunciado)
        self.xp_para_evoluir = xp_para_evoluir  # None se for a fase final
        self.evolui_para = evolui_para  # id da próxima Especie, ou None

    def __repr__(self):
        return f"Especie({self.id!r}, fase={self.fase}, tipos={self.tipos})"


class Pokedex:
    """
    Registro de todas as espécies conhecidas na região (a "cadeia de
    evolução" completa de cada linha evolutiva), carregado a partir do
    arquivo de configuração da região.
    """

    def __init__(self):
        self._especies: Dict[str, Especie] = {}

    def registrar(self, especie: Especie):
        self._especies[especie.id] = especie

    def obter(self, id_especie: str) -> Especie:
        return self._especies[id_especie]

    def existe(self, id_especie: str) -> bool:
        return id_especie in self._especies

    def especies_fase_inicial(self) -> List[Especie]:
        """Espécies de fase 1 -- são as únicas entregues pelo Professor
        Carvalho a um treinador iniciante, conforme o enunciado."""
        return [e for e in self._especies.values() if e.fase == 1]

    def todas(self) -> List[Especie]:
        return list(self._especies.values())

    def proxima_evolucao(self, especie: Especie) -> Optional[Especie]:
        if especie.evolui_para is None:
            return None
        return self._especies.get(especie.evolui_para)


# --------------------------------------------------------------------- #
# Tabela de vantagens de tipo (item extra / bônus do enunciado: "Quais
# tipos têm vantagens sobre quais outros e como são representados").
#
# Representação escolhida: dicionário tipo_atacante -> {tipo_defensor: mult}.
# Multiplicador 2.0 = super efetivo (dobro de dano), 0.5 = pouco efetivo
# (metade do dano), 1.0 = neutro (padrão quando o par não está listado).
# Isso cobre um subconjunto simplificado, mas fiel às vantagens clássicas
# da franquia Pokémon, o suficiente para demonstrar a mecânica pedida.
# --------------------------------------------------------------------- #
TABELA_TIPOS: Dict[str, Dict[str, float]] = {
    "agua":     {"fogo": 2.0, "terra": 2.0, "grama": 0.5, "agua": 0.5},
    "fogo":     {"grama": 2.0, "gelo": 2.0, "agua": 0.5, "fogo": 0.5, "pedra": 0.5},
    "grama":    {"agua": 2.0, "terra": 2.0, "pedra": 2.0, "fogo": 0.5, "grama": 0.5, "venenoso": 0.5, "voador": 0.5},
    "eletrico": {"agua": 2.0, "voador": 2.0, "grama": 0.5, "eletrico": 0.5, "terra": 0.0},
    "venenoso": {"grama": 2.0, "venenoso": 0.5, "terra": 0.5, "pedra": 0.5, "fantasma": 0.5},
    "voador":   {"grama": 2.0, "venenoso": 2.0, "eletrico": 0.5, "pedra": 0.5},
    "fantasma": {"fantasma": 2.0, "psiquico": 2.0, "normal": 0.0},
    "psiquico": {"venenoso": 2.0, "lutador": 2.0, "psiquico": 0.5},
    "terra":    {"fogo": 2.0, "eletrico": 2.0, "venenoso": 2.0, "pedra": 2.0, "grama": 0.5, "voador": 0.0},
    "pedra":    {"fogo": 2.0, "voador": 2.0, "gelo": 2.0, "lutador": 0.5, "terra": 0.5},
    "gelo":     {"grama": 2.0, "terra": 2.0, "voador": 2.0, "agua": 0.5, "gelo": 0.5, "fogo": 0.5},
    "lutador":  {"normal": 2.0, "pedra": 2.0, "gelo": 2.0, "voador": 0.5, "psiquico": 0.5, "venenoso": 0.5, "fantasma": 0.0},
    "normal":   {"fantasma": 0.0},
}


def multiplicador_de_dano(tipos_atacante: List[str], tipos_defensor: List[str]) -> float:
    """
    Calcula o multiplicador de dano total considerando TODOS os tipos do
    atacante contra TODOS os tipos do defensor (efeitos combinados são
    multiplicados entre si, igual à série principal Pokémon).
    Retorna 1.0 (neutro) quando não há entradas na tabela para o par de tipos.
    """
    multiplicador_total = 1.0
    for t_atk in tipos_atacante:
        tabela_atk = TABELA_TIPOS.get(t_atk, {})
        for t_def in tipos_defensor:
            multiplicador_total *= tabela_atk.get(t_def, 1.0)
    return multiplicador_total
