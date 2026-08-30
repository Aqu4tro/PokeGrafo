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
from models.item import Ovo


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
        self.pokemons_pendentes: List[Pokemon] = []  # aguardam escolha manual de excedente
        self.selvagens_ocultos = set()  # abandonados em captura durante esta jornada

        self.insignias: List[str] = []            # ids dos ginásios vencidos
        self.xp: float = 0.0
        self.distancia_percorrida: float = 0.0    # também funciona como "relógio" do treinador
        self.tempo_decorrido: float = 0.0
        self.tem_incubadora: bool = True
        self.pokebolas: int = 7
        self.inscrito_na_liga: bool = False
        self.registrado_status: Optional[str] = None  # "sucesso" | "fora_do_prazo"
        self.transito_origem: Optional[str] = None
        self.transito_destino: Optional[str] = None
        self.transito_tempo_total: float = 0.0
        self.transito_tempo_restante: float = 0.0

    # ------------------------------------------------------------------ #
    # Equipe de pokémons
    # ------------------------------------------------------------------ #
    def pokemons_disponiveis(self) -> List[Pokemon]:
        return [p for p in self.equipe if p.esta_disponivel()]

    def pode_batalhar_treinador(self) -> bool:
        """É necessário possuir ao menos 3 pokémons conscientes para desafiar
        outro treinador (regra explícita do enunciado)."""
        return len(self.pokemons_disponiveis()) >= 3

    @property
    def pokebolas_extras(self) -> int:
        """Alias de compatibilidade para versões anteriores da GUI."""
        return self.pokebolas

    @pokebolas_extras.setter
    def pokebolas_extras(self, valor: int):
        self.pokebolas = valor

    def adicionar_pokemon(self, pokemon: Pokemon,
                          enviar_ao_professor: Optional[Pokemon] = None) -> str:
        """
        Adiciona um pokémon à equipe. Se a equipe estiver cheia, a chamada
        deve informar manualmente qual Pokémon, entre a equipe e o novo,
        será enviado ao Professor Carvalho.
        """
        candidatos = self.equipe + [pokemon]
        if len(candidatos) > self.MAX_POKEMONS_ATIVOS:
            if enviar_ao_professor not in candidatos:
                raise ValueError("Escolha manualmente qual Pokémon será enviado ao Professor Carvalho.")
            if enviar_ao_professor is not pokemon:
                self.equipe.remove(enviar_ao_professor)
            enviar_ao_professor.treinador_id = None
            self.deposito_professor.append(enviar_ao_professor)
            if enviar_ao_professor is pokemon:
                return (f"{pokemon.apelido} foi enviado ao Prof. Carvalho; "
                        "a equipe permaneceu inalterada.")

        pokemon.treinador_id = self.id
        pokemon.vertice_atual = self.vertice_atual
        self.equipe.append(pokemon)
        mensagem = f"{self.nome} adicionou {pokemon.apelido} à equipe."
        if enviar_ao_professor is not None:
            mensagem += f" {enviar_ao_professor.apelido} foi enviado ao Prof. Carvalho."
        return mensagem

    def colocar_pokemon_pendente(self, pokemon: Pokemon):
        pokemon.treinador_id = self.id
        pokemon.vertice_atual = self.vertice_atual
        self.pokemons_pendentes.append(pokemon)

    def resolver_pokemon_pendente(self, pokemon: Pokemon,
                                  enviar_ao_professor: Pokemon) -> str:
        if pokemon not in self.pokemons_pendentes:
            raise ValueError("O Pokémon informado não está pendente.")
        mensagem = self.adicionar_pokemon(pokemon, enviar_ao_professor)
        self.pokemons_pendentes.remove(pokemon)
        return mensagem

    def pode_carregar_mais_um_ovo(self) -> bool:
        return (len(self.equipe) + len(self.ovos) + len(self.pokemons_pendentes)
                < self.MAX_TOTAL_COM_OVOS)

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
    @property
    def em_transito(self) -> bool:
        return self.transito_destino is not None

    @property
    def progresso_transito(self) -> float:
        if not self.em_transito or self.transito_tempo_total <= 0:
            return 0.0
        consumido = self.transito_tempo_total - self.transito_tempo_restante
        return max(0.0, min(1.0, consumido / self.transito_tempo_total))

    def iniciar_transito(self, destino: str, peso_aresta: float):
        """Registra uma viagem sem antecipar a chegada ao destino."""
        if self.em_transito:
            raise ValueError(f"{self.nome} já está em trânsito.")
        if peso_aresta <= 0:
            raise ValueError("O tempo de uma aresta deve ser positivo.")
        self.transito_origem = self.vertice_atual
        self.transito_destino = destino
        self.transito_tempo_total = float(peso_aresta)
        self.transito_tempo_restante = float(peso_aresta)

    def _avancar_percurso(self, unidades: float,
                          rng: Optional[random.Random] = None):
        rng = rng or random
        self.distancia_percorrida += unidades
        self.tempo_decorrido += unidades
        eventos = []
        for pokemon in self.equipe:
            pokemon.tick(unidades, rng, distancia_percorrida=unidades)
        for ovo in list(self.ovos):
            if ovo.avancar_incubacao(unidades):
                eventos.append(("ovo_chocou", ovo))
        return eventos

    def avancar_transito(self, unidades: float,
                         rng: Optional[random.Random] = None):
        """Consome a duração da aresta e materializa a chegada ao fim dela."""
        if not self.em_transito or unidades <= 0:
            return False, []
        consumido = min(float(unidades), self.transito_tempo_restante)
        self.transito_tempo_restante -= consumido
        eventos = self._avancar_percurso(consumido, rng)
        if self.transito_tempo_restante > 0:
            return False, eventos
        self.vertice_atual = self.transito_destino
        for pokemon in self.equipe:
            pokemon.vertice_atual = self.vertice_atual
        self.cancelar_transito()
        return True, eventos

    def cancelar_transito(self):
        self.transito_origem = None
        self.transito_destino = None
        self.transito_tempo_total = 0.0
        self.transito_tempo_restante = 0.0

    def mover_para(self, novo_vertice: str, peso_aresta: float, rng: Optional[random.Random] = None):
        """Move o treinador um vértice, avança seu relógio (distância
        percorrida) e propaga o tick de tempo para toda a sua equipe e
        ovos carregados (regeneração de HP, XP por distância, incubação)."""
        if self.em_transito:
            raise ValueError(f"{self.nome} não pode iniciar outra viagem enquanto está em trânsito.")
        if peso_aresta <= 0:
            raise ValueError("O tempo de uma aresta deve ser positivo.")
        rng = rng or random
        self.vertice_atual = novo_vertice
        eventos = self._avancar_percurso(peso_aresta, rng)
        for pokemon in self.equipe:
            pokemon.vertice_atual = novo_vertice
        return eventos

    def avancar_parado(self, unidades: float, em_pmc: bool,
                       rng: Optional[random.Random] = None):
        """Avança tempo sem caminhar; tratamento progride apenas no PMC."""
        rng = rng or random
        self.tempo_decorrido += unidades
        for pokemon in self.equipe:
            pokemon.tick(
                unidades, rng, em_tratamento_estacionario=em_pmc,
                distancia_percorrida=0.0)

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
        estado = (f"Em trânsito para {self.transito_destino} "
                  f"({self.transito_tempo_restante:g} restantes)"
                  if self.em_transito else f"Local: {self.vertice_atual}")
        if self.registrado_status == "fora_do_prazo":
            estado += " | Inapto para a Liga"
        return (f"{self.nome} | XP {self.xp:.0f} | Insígnias: {len(self.insignias)} "
                f"| Equipe: {len(self.equipe)}/{self.MAX_POKEMONS_ATIVOS} | "
                f"Ovos: {len(self.ovos)} | Pokébolas: {self.pokebolas} | "
                f"{estado}")

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
        self._tempo_restante_no_ginasio = float(tempo_permanencia)
        self._patrulhando = False
        self._retornando_ao_ginasio = False

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
        self.vertice_ultimo_ataque: Optional[str] = None
        self.itens_roubados: List[Pokemon] = []

    def tornar_invisivel(self, duracao: float, origem_fuga: Optional[str] = None):
        self.cancelar_transito()
        self.invisivel = True
        self._timer_invisivel = duracao
        self.vertice_ultimo_ataque = origem_fuga or self.vertice_atual

    def avancar_invisibilidade(self, unidades: float):
        if self.invisivel:
            self._timer_invisivel -= unidades
            if self._timer_invisivel <= 0:
                self.invisivel = False
                self._timer_invisivel = 0.0
