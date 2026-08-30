"""
models/regiao.py
=================
Classe `Regiao`: agrega o grafo do mapa, a Pokédex (cadeias de evolução),
os treinadores (incluindo líderes de ginásio e Equipe Rocket), os pokémons
selvagens e os itens espalhados pelo mapa, além do prazo máximo de
inscrição na Liga.

É o "mundo" da simulação -- o motor de simulação (engine/simulacao.py) e a
interface gráfica (gui/app.py) operam sobre um objeto `Regiao`.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from models.grafo import Grafo
from models.especie import Pokedex
from models.pokemon import Pokemon
from models.treinador import Treinador, LiderGinasio, MembroEquipeRocket
from models.item import Item


class Regiao:
    def __init__(self, nome: str, grafo: Grafo, pokedex: Pokedex,
                 vertice_laboratorio: str, prazo_maximo_inscricao: float):
        self.nome = nome
        self.grafo = grafo
        self.pokedex = pokedex
        self.vertice_laboratorio = vertice_laboratorio
        self.prazo_maximo_inscricao = prazo_maximo_inscricao

        self.treinadores: Dict[int, Treinador] = {}
        self.pokemons_selvagens: Dict[int, Pokemon] = {}
        self.itens: Dict[int, Item] = {}

        self.tempo_global: float = 0.0
        self.log_eventos: List[str] = []

    # ------------------------------------------------------------------ #
    # Registro de entidades
    # ------------------------------------------------------------------ #
    def adicionar_treinador(self, treinador: Treinador):
        self.treinadores[treinador.id] = treinador

    def adicionar_pokemon_selvagem(self, pokemon: Pokemon, vertice_id: str):
        pokemon.vertice_atual = vertice_id
        pokemon.treinador_id = None
        self.pokemons_selvagens[pokemon.id] = pokemon

    def adicionar_item(self, item: Item):
        self.itens[item.id] = item

    def registrar_log(self, mensagem: str):
        self.log_eventos.append(mensagem)
        if len(self.log_eventos) > 500:
            self.log_eventos = self.log_eventos[-500:]

    # ------------------------------------------------------------------ #
    # Consultas sobre o mapa
    # ------------------------------------------------------------------ #
    def lideres_ginasio(self) -> List[LiderGinasio]:
        return [t for t in self.treinadores.values() if isinstance(t, LiderGinasio)]

    def membros_rocket(self) -> List[MembroEquipeRocket]:
        return [t for t in self.treinadores.values() if isinstance(t, MembroEquipeRocket)]

    def treinadores_comuns(self) -> List[Treinador]:
        return [t for t in self.treinadores.values()
                if not isinstance(t, (LiderGinasio, MembroEquipeRocket))]

    def total_ginasios(self) -> int:
        return len(self.grafo.vertices_por_tipo("ginasio"))

    def vertices_pmc(self) -> List[str]:
        return [v.id for v in self.grafo.vertices_por_tipo("pmc")]

    def vertices_estadio(self) -> List[str]:
        return [v.id for v in self.grafo.vertices_por_tipo("estadio")]

    def batalha_permitida_em(self, vertice_id: str) -> bool:
        """Batalhas são proibidas no PMC e no laboratório do Professor
        Carvalho (Requisito 7)."""
        if not self.grafo.existe_vertice(vertice_id):
            return False
        tipo = self.grafo.obter_vertice(vertice_id).tipo
        return tipo not in ("pmc", "laboratorio")

    # ------------------------------------------------------------------ #
    # O que está presente em um vértice (usado pela GUI para montar as
    # opções de ação disponíveis para o jogador)
    # ------------------------------------------------------------------ #
    def pokemons_selvagens_em(self, vertice_id: str) -> List[Pokemon]:
        return [p for p in self.pokemons_selvagens.values()
                if p.vertice_atual == vertice_id]

    def itens_em(self, vertice_id: str) -> List[Item]:
        return [i for i in self.itens.values()
                if i.vertice_atual == vertice_id and not i.coletado]

    def treinadores_em(self, vertice_id: str, excluir_id: Optional[int] = None) -> List[Treinador]:
        return [t for t in self.treinadores.values()
                if t.vertice_atual == vertice_id and t.id != excluir_id
                and not (isinstance(t, MembroEquipeRocket) and t.invisivel)]

    def remover_pokemon_selvagem(self, pokemon_id: int):
        self.pokemons_selvagens.pop(pokemon_id, None)

    def remover_item(self, item_id: int):
        self.itens.pop(item_id, None)
