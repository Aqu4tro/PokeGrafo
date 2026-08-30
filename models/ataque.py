"""Ataques disponíveis durante os duelos Pokémon.

O enunciado exige que o treinador escolha um ataque conhecido pelo Pokémon.
Ataques são objetos imutáveis usados para representar essa escolha. O campo
``poder`` é apenas metadado do repertório: o dano obrigatório é calculado
exclusivamente por ``max(0, AP efetivo - DP efetivo)``.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Ataque:
    nome: str
    poder: float
    tipo: Optional[str] = None
    dano_minimo: float = 0.0


INVESTIDA = Ataque("Investida", poder=25.0)
ESFORCO = Ataque("Esforço", poder=0.0)


def ataques_para(tipos, fase: int):
    """Monta o repertório da fase sem depender da interface gráfica."""
    ataques = [INVESTIDA]
    for tipo in tipos:
        ataques.append(Ataque(f"Golpe de {tipo}", poder=30.0 + 5.0 * (fase - 1), tipo=tipo))
    if fase >= 2:
        ataques.append(Ataque("Ataque evoluído", poder=40.0 + 5.0 * (fase - 2), tipo=tipos[0] if tipos else None))
    # Esforço é uma escolha válida, mas nunca cria dano mínimo artificial.
    ataques.append(ESFORCO)
    return ataques
