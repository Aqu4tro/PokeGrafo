"""
models/treinador.py
====================
Classe `Treinador` e suas especializações `LiderGinasio` (líder de ginásio)
e `MembroEquipeRocket` (item extra do enunciado).

Usa herança (POO) para modelar as diferenças de comportamento entre um
treinador comum, um líder de ginásio (fica associado a um ginásio e pode
patrulhar a região) e um membro da Equipe Rocket (rouba pokémons/insígnias
e foge/reaparece quando derrotado ou vitorioso).
"""

from __future__ import annotations
import random
from typing import List, Optional, Dict

from models.pokemon import Pokemon
from models.item import Ovo, PokebolaExtra


class Treinador:
    MAX_POKEMONS_ATIVOS = 6
    MAX_TOTAL_COM_OVOS = 7

    _proximo_id = 1

    def __init__(self, nome: str, vertice_inicial: str, eh_jogador: bool = False):
        self.id = Treinador._proximo_id
        Treinador._proximo_id += 1

        self.nome = nome
        self.vertice_atual = vertice_inicial
        self.eh_jogador = eh_jogador  # True = controlado pelo usuário na GUI

        self.equipe: List[Pokemon] = []          # pokémons ativos (máx. 6)
        self.deposito_professor: List[Pokemon] = []  # excedente enviado ao Prof. Carvalho
        self.ovos: List[Ovo] = []                 # ovos não chocados carregados

        self.insignias: List[str] = []            # ids dos ginásios vencidos
        self.xp: float = 0.0
        self.distancia_percorrida: float = 0.0    # também funciona como "relógio" do treinador
        self.tem_incubadora: bool = True
        self.pokebolas_extras: int = 0
        self.inscrito_na_liga: bool = False
        self.registrado_status: Optional[str] = None  # "sucesso" | "fora_do_prazo"

    # ------------------------------------------------------------------ #
    # Equipe de pokémons
    # ------------------------------------------------------------------ #
    def pokemons_disponiveis(self) -> List[Pokemon]:
        return [p for p in self.equipe if p.esta_disponivel()]

    def pode_batalhar_treinador(self) -> bool:
        """É necessário possuir ao menos 3 pokémons conscientes para desafiar
        outro treinador (regra explícita do enunciado)."""
        return len(self.pokemons_disponiveis()) >= 3

    def adicionar_pokemon(self, pokemon: Pokemon, rng: Optional[random.Random] = None) -> str:
        """
        Adiciona um pokémon à equipe. Se isso ultrapassar o limite de 6
        pokémons ativos, o(s) de menor XP são enviados ao depósito do
        Professor Carvalho (política padrão de desempate; a GUI também
        permite ao jogador escolher manualmente quem mantém).
        """
        pokemon.treinador_id = self.id
        pokemon.vertice_atual = self.vertice_atual
        self.equipe.append(pokemon)
        mensagem = f"{self.nome} adicionou {pokemon.apelido} à equipe."
        if len(self.equipe) > self.MAX_POKEMONS_ATIVOS:
            self.equipe.sort(key=lambda p: p.xp, reverse=True)
            excedentes = self.equipe[self.MAX_POKEMONS_ATIVOS:]
            self.equipe = self.equipe[:self.MAX_POKEMONS_ATIVOS]
            for exc in excedentes:
                exc.treinador_id = None
                self.deposito_professor.append(exc)
            nomes = ", ".join(e.apelido for e in excedentes)
            mensagem += f" Excedente enviado ao Prof. Carvalho: {nomes}."
        return mensagem

    def pode_carregar_mais_um_ovo(self) -> bool:
        return (len(self.equipe) + len(self.ovos)) < self.MAX_TOTAL_COM_OVOS

    def adicionar_ovo(self, ovo: Ovo) -> bool:
        if not self.pode_carregar_mais_um_ovo():
            return False
        ovo.coletado = True
        self.ovos.append(ovo)
        return True

    def usar_erva_em_todos(self):
        for p in self.equipe:
            p.usar_erva()

    # ------------------------------------------------------------------ #
    # Movimento / passagem de tempo
    # ------------------------------------------------------------------ #
    def mover_para(self, novo_vertice: str, peso_aresta: float, rng: Optional[random.Random] = None):
        """Move o treinador um vértice, avança seu relógio (distância
        percorrida) e propaga o tick de tempo para toda a sua equipe e
        ovos carregados (regeneração de HP, XP por distância, incubação)."""
        rng = rng or random
        self.vertice_atual = novo_vertice
        self.distancia_percorrida += peso_aresta

        eventos = []
        for p in self.equipe:
            p.vertice_atual = novo_vertice
            p.tick(peso_aresta, rng)

        for ovo in list(self.ovos):
            if ovo.avancar_incubacao(peso_aresta):
                eventos.append(("ovo_chocou", ovo))
        return eventos

    # ------------------------------------------------------------------ #
    # Insígnias / Liga
    # ------------------------------------------------------------------ #
    def conquistar_insignia(self, id_ginasio: str):
        if id_ginasio not in self.insignias:
            self.insignias.append(id_ginasio)  # permanente, mesmo perdendo depois

    def numero_insignias_necessarias(self, total_ginasios_regiao: int) -> int:
        return min(8, total_ginasios_regiao)

    def apto_para_inscricao(self, total_ginasios_regiao: int) -> bool:
        return len(self.insignias) >= self.numero_insignias_necessarias(total_ginasios_regiao)

    # ------------------------------------------------------------------ #
    # XP do treinador (regra de batalhas entre treinadores)
    # ------------------------------------------------------------------ #
    def registrar_vitoria_treinador(self, xp_oponente: float):
        if xp_oponente >= self.xp:
            self.xp += 3
        else:
            self.xp += 1

    def registrar_captura_bem_sucedida(self):
        self.xp += 3

    def resumo(self) -> str:
        return (f"{self.nome} | XP {self.xp:.0f} | Insígnias: {len(self.insignias)} "
                f"| Equipe: {len(self.equipe)}/{self.MAX_POKEMONS_ATIVOS} | "
                f"Ovos: {len(self.ovos)} | Local: {self.vertice_atual}")

    def __repr__(self):
        return f"Treinador(#{self.id}, {self.nome!r})"


class LiderGinasio(Treinador):
    """
    Líder de um ginásio. Pode ser fixo (sempre no ginásio) ou móvel: nesse
    caso, patrulha vértices vizinhos e retorna periodicamente ao ginásio,
    permanecendo lá por um tempo determinado antes de sair novamente
    (conforme descrito no enunciado).
    """

    def __init__(self, nome: str, vertice_ginasio: str, id_insignia: str,
                 fixo: bool = True, tempo_permanencia: float = 30.0):
        super().__init__(nome, vertice_ginasio, eh_jogador=False)
        self.vertice_ginasio = vertice_ginasio
        self.id_insignia = id_insignia
        self.fixo = fixo
        self.tempo_permanencia_no_ginasio = tempo_permanencia
        self._tempo_restante_fora = 0.0
        self._patrulhando = False

    def esta_no_ginasio(self) -> bool:
        return self.vertice_atual == self.vertice_ginasio


class MembroEquipeRocket(Treinador):
    """
    Item extra do enunciado: um membro da Equipe Rocket rouba pokémons
    e/ou insígnias de outros treinadores. Ao ser derrotado, é reenviado
    para um lugar aleatório e distante do ponto de ataque (calculado via
    `AlgoritmosGrafo.vertice_mais_distante`). Ao vencer um roubo, foge e
    fica invisível por um tempo, reaparecendo depois em outro lugar.
    """

    def __init__(self, nome: str, vertice_inicial: str):
        super().__init__(nome, vertice_inicial, eh_jogador=False)
        self.invisivel = False
        self._timer_invisivel = 0.0
        self.itens_roubados: List[Pokemon] = []

    def tornar_invisivel(self, duracao: float):
        self.invisivel = True
        self._timer_invisivel = duracao

    def avancar_invisibilidade(self, unidades: float):
        if self.invisivel:
            self._timer_invisivel -= unidades
            if self._timer_invisivel <= 0:
                self.invisivel = False
                self._timer_invisivel = 0.0
