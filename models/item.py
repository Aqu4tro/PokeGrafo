"""
models/item.py
===============
Itens espalhados pela região: ervas medicinais, ovos de pokémon selvagens e
itens extras genéricos (pokébolas sobressalentes), conforme o Requisito
Adicional 4 ("o arquivo também indica quantos pokémons, treinadores e itens
extras existem na região... deve ser escolhido de forma aleatória").
"""

from __future__ import annotations
import random
from typing import Optional

from models.especie import Especie


class TipoItem:
    ERVA = "erva"
    OVO = "ovo"
    POKEBOLA_EXTRA = "pokebola_extra"


class Item:
    _proximo_id = 1

    def __init__(self, tipo: str, vertice_atual: str):
        self.id = Item._proximo_id
        Item._proximo_id += 1
        self.tipo = tipo
        self.vertice_atual = vertice_atual
        self.coletado = False

    def __repr__(self):
        return f"Item(#{self.id}, {self.tipo}, em={self.vertice_atual})"


class Ovo(Item):
    """
    Ovo de pokémon selvagem. O tipo/espécie verdadeiro é sorteado no
    momento da criação do ovo, mas fica OCULTO do treinador até chocar
    ("o tipo de pokémon do ovo encontrado é desconhecido até ser chocado").
    """
    DISTANCIA_PARA_CHOCAR = 100.0

    def __init__(self, vertice_atual: str, especie_oculta: Especie, rng: Optional[random.Random] = None):
        super().__init__(TipoItem.OVO, vertice_atual)
        self._especie_oculta = especie_oculta
        self._progresso = 0.0
        self._rng = rng or random

    def avancar_incubacao(self, unidades: float) -> bool:
        """Avança o progresso de incubação. Retorna True se o ovo chocou agora."""
        if self.coletado is False:
            return False
        self._progresso += unidades
        return self._progresso >= self.DISTANCIA_PARA_CHOCAR

    def chocar(self):
        """Revela a espécie oculta -- usado pelo motor de simulação para
        criar o Pokemon real no momento em que a incubação termina."""
        return self._especie_oculta

    def progresso_percentual(self) -> float:
        return min(100.0, 100.0 * self._progresso / self.DISTANCIA_PARA_CHOCAR)


class Erva(Item):
    def __init__(self, vertice_atual: str):
        super().__init__(TipoItem.ERVA, vertice_atual)


class PokebolaExtra(Item):
    """Item extra genérico: uma pokébola sobressalente encontrada na região."""

    def __init__(self, vertice_atual: str):
        super().__init__(TipoItem.POKEBOLA_EXTRA, vertice_atual)
