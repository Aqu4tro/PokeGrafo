"""Motor da simulação e autoridade das regras de domínio do PokeGrafo."""

from __future__ import annotations
import random
from typing import Callable, List, Optional, Tuple

from models.batalha import (
    DecisorAbandonoCaptura, DecisorDesistencia, ResultadoDuelo, SeletorAtaque,
    SeletorSubstituto, SistemaBatalha,
)
from models.grafo import AlgoritmosGrafo
from models.item import Erva, Ovo, PokebolaExtra
from models.pokemon import Pokemon, StatusPokemon
from models.regiao import Regiao
from models.treinador import LiderGinasio, MembroEquipeRocket, Treinador

SeletorExcedente = Callable[[Treinador, List[Pokemon]], Pokemon]


class Simulacao:
    def __init__(self, regiao: Regiao, seed: Optional[int] = None):
        self.regiao = regiao
        self.rng = random.Random(seed)
        self.jogador: Optional[Treinador] = None

    # ------------------------------------------------------------------ #
    # Criação do jogador
    # ------------------------------------------------------------------ #
    def especies_iniciais_disponiveis(self):
        configuradas = list(getattr(self.regiao, "especies_iniciais", []))
        return configuradas or self.regiao.pokedex.especies_fase_inicial()

    def _tres_iniciais_classicos(self):
        candidatas = self.especies_iniciais_disponiveis()
        escolhidas = []
        for tipo in ("agua", "fogo", "grama"):
            especie = next((e for e in candidatas if tipo in e.tipos and e.fase == 1), None)
            if especie is None:
                raise ValueError(f"Não há espécie inicial de fase 1 do tipo {tipo}.")
            escolhidas.append(especie)
        if len({e.id for e in escolhidas}) != 3:
            raise ValueError("Os três Pokémon iniciais devem ser espécies distintas.")
        return escolhidas

    def criar_jogador(self, nome: str, aceitar_tres_iniciais: bool = True) -> Treinador:
        jogador = Treinador(nome, self.regiao.vertice_laboratorio, eh_jogador=True)
        if aceitar_tres_iniciais:
            especies = self._tres_iniciais_classicos()
        else:
            disponiveis = self.regiao.pokedex.especies_fase_inicial()
            if not disponiveis:
                raise ValueError("O laboratório não possui Pokémon de fase inicial.")
            especies = [self.rng.choice(disponiveis)]
        for especie in especies:
            jogador.adicionar_pokemon(
                Pokemon(especie, self.regiao.pokedex, hp=100, xp=0.0, rng=self.rng))
        self.regiao.adicionar_treinador(jogador)
        self.jogador = jogador
        self.regiao.registrar_log(
            f"{nome} iniciou a jornada com {len(jogador.equipe)} Pokémon e 7 Pokébolas.")
        return jogador

    # ------------------------------------------------------------------ #
    # Movimento e tempo sincronizado
    # ------------------------------------------------------------------ #
    def vizinhos_de(self, treinador: Treinador) -> List[Tuple[str, float]]:
        return self.regiao.grafo.vizinhos(treinador.vertice_atual)

    def calcular_rota(self, origem: str, destino: str) -> Tuple[List[str], float]:
        return AlgoritmosGrafo.caminho_minimo(self.regiao.grafo, origem, destino)

    def mover_um_passo(self, treinador: Treinador, vertice_destino: str,
                       seletor_excedente: Optional[SeletorExcedente] = None) -> List[str]:
        origem = treinador.vertice_atual
        vizinhos = dict(self.regiao.grafo.vizinhos(origem))
        if vertice_destino not in vizinhos:
            raise ValueError(f"{vertice_destino} não é adjacente a {origem}.")
        peso = vizinhos[vertice_destino]
        eventos = treinador.mover_para(vertice_destino, peso, self.rng)
        mensagens = [f"{treinador.nome} vai de {origem} para {vertice_destino} (custo {peso:g})."]
        mensagens.extend(self._processar_eventos_ovo(treinador, eventos, seletor_excedente))
        for mensagem in mensagens:
            self.regiao.registrar_log(mensagem)
        # Toda viagem do jogador avança o mesmo relógio usado pelo mundo.
        if treinador.eh_jogador:
            self._atualizar_status_prazo(treinador)
            mensagens.extend(self.avancar_mundo(peso))
        return mensagens

    def _processar_eventos_ovo(self, treinador: Treinador, eventos,
                               seletor_excedente: Optional[SeletorExcedente]) -> List[str]:
        mensagens = []
        for tipo_evento, ovo in eventos:
            if tipo_evento != "ovo_chocou":
                continue
            pokemon = Pokemon(ovo.chocar(), self.regiao.pokedex, hp=100, xp=0.0, rng=self.rng)
            treinador.ovos.remove(ovo)
            if len(treinador.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
                mensagens.append(f"Um ovo chocou! {treinador.adicionar_pokemon(pokemon)}")
                continue
            if seletor_excedente:
                escolhido = seletor_excedente(treinador, treinador.equipe + [pokemon])
                mensagens.append(f"Um ovo chocou! {treinador.adicionar_pokemon(pokemon, escolhido)}")
            else:
                treinador.colocar_pokemon_pendente(pokemon)
                mensagens.append(
                    f"Um ovo chocou e revelou {pokemon.apelido}; escolha manualmente o excedente.")
        return mensagens

    def resolver_excedente(self, treinador: Treinador, pokemon_pendente: Pokemon,
                           enviar_ao_professor: Pokemon) -> str:
        mensagem = treinador.resolver_pokemon_pendente(
            pokemon_pendente, enviar_ao_professor)
        self.regiao.registrar_log(mensagem)
        return mensagem

    def avancar_mundo(self, unidades: float = 1.0,
                      treinador_parado: Optional[Treinador] = None) -> List[str]:
        if unidades < 0:
            raise ValueError("O tempo não pode avançar um valor negativo.")
        mensagens = []
        restante = float(unidades)
        while restante > 0:
            passo = min(1.0, restante)
            restante -= passo
            self.regiao.tempo_global += passo
            if treinador_parado is not None:
                vertice = self.regiao.grafo.obter_vertice(treinador_parado.vertice_atual)
                treinador_parado.avancar_parado(
                    passo, em_pmc=vertice.tipo == "pmc", rng=self.rng)
                self._atualizar_status_prazo(treinador_parado)
            for lider in self.regiao.lideres_ginasio():
                mensagens.extend(self._tick_lider_ginasio(lider, passo))
            for comum in self.regiao.treinadores_comuns():
                if not comum.eh_jogador:
                    mensagens.extend(self._tick_treinador_npc(comum, passo))
            for rocket in self.regiao.membros_rocket():
                mensagens.extend(self._tick_rocket(rocket, passo))
            mensagens.extend(self._tick_pokemons_selvagens(passo))
        for mensagem in mensagens:
            self.regiao.registrar_log(mensagem)
        return mensagens

    def _avancar_movimento_treinador(
            self, treinador: Treinador, passo: float,
            destino_preferido: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Inicia/avança uma única aresta sem antecipar a posição final."""
        if not treinador.em_transito:
            vizinhos = dict(self.regiao.grafo.vizinhos(treinador.vertice_atual))
            if not vizinhos:
                return False, None
            destino = (destino_preferido if destino_preferido in vizinhos
                       else self.rng.choice(list(vizinhos)))
            treinador.iniciar_transito(destino, vizinhos[destino])
        destino = treinador.transito_destino
        chegou, eventos = treinador.avancar_transito(passo, self.rng)
        self._processar_eventos_ovo(treinador, eventos, None)
        return chegou, destino

    def _tick_lider_ginasio(self, lider: LiderGinasio, passo: float) -> List[str]:
        if lider.fixo:
            return []
        mensagens = []
        if lider.em_transito:
            chegou, destino = self._avancar_movimento_treinador(lider, passo)
            if lider._patrulhando:
                lider._tempo_restante_fora -= passo
            if chegou:
                mensagens.append(f"{lider.nome} chegou a {destino}.")
                if lider._retornando_ao_ginasio and lider.esta_no_ginasio():
                    lider._retornando_ao_ginasio = False
                    lider._tempo_restante_no_ginasio = lider.tempo_permanencia_no_ginasio
                    mensagens.append(
                        f"{lider.nome} retornou ao ginásio por "
                        f"{lider.tempo_permanencia_no_ginasio:g} unidades.")
            if lider._patrulhando and lider._tempo_restante_fora <= 0:
                lider._patrulhando = False
                lider._retornando_ao_ginasio = True
            return mensagens
        if lider._retornando_ao_ginasio:
            if lider.esta_no_ginasio():
                lider._retornando_ao_ginasio = False
                lider._tempo_restante_no_ginasio = lider.tempo_permanencia_no_ginasio
                return mensagens
            caminho, _ = AlgoritmosGrafo.caminho_minimo(
                self.regiao.grafo, lider.vertice_atual, lider.vertice_ginasio)
            if len(caminho) >= 2:
                chegou, destino = self._avancar_movimento_treinador(
                    lider, passo, caminho[1])
                mensagens.append(
                    f"{lider.nome} está retornando ao ginásio via {destino}.")
                if chegou and lider.esta_no_ginasio():
                    lider._retornando_ao_ginasio = False
                    lider._tempo_restante_no_ginasio = lider.tempo_permanencia_no_ginasio
            return mensagens
        if lider.esta_no_ginasio() and not lider._patrulhando:
            lider._tempo_restante_no_ginasio -= passo
            if lider._tempo_restante_no_ginasio <= 0:
                lider._patrulhando = True
                lider._tempo_restante_fora = self.rng.uniform(15, 40)
                mensagens.append(f"{lider.nome} iniciou uma patrulha.")
            return mensagens
        if lider._patrulhando:
            lider._tempo_restante_fora -= passo
            if lider._tempo_restante_fora <= 0:
                lider._patrulhando = False
                lider._retornando_ao_ginasio = True
                mensagens.append(f"{lider.nome} encerrou a patrulha e iniciou o retorno.")
                return mensagens
            chegou, destino = self._avancar_movimento_treinador(lider, passo)
            estado = "chegou" if chegou else "está em trânsito para"
            mensagens.append(f"{lider.nome} {estado} {destino}.")
        return mensagens

    def _tick_treinador_npc(self, treinador: Treinador, passo: float) -> List[str]:
        chegou, destino = self._avancar_movimento_treinador(treinador, passo)
        if destino is None:
            return []
        if chegou:
            return [f"{treinador.nome} chegou a {destino}."]
        return [f"{treinador.nome} está em trânsito para {destino}."]

    def _tick_pokemons_selvagens(self, passo: float) -> List[str]:
        mensagens = []
        for pokemon in list(self.regiao.pokemons_selvagens.values()):
            if not pokemon.em_transito:
                vizinhos = self.regiao.grafo.vizinhos(pokemon.vertice_atual)
                if not vizinhos:
                    continue
                destino, peso = self.rng.choice(vizinhos)
                pokemon.iniciar_transito(destino, peso)
            destino = pokemon.transito_destino
            chegou = pokemon.avancar_transito(passo, self.rng)
            if chegou:
                mensagens.append(f"{pokemon.apelido} selvagem chegou a {destino}.")
        return mensagens

    def _tick_rocket(self, rocket: MembroEquipeRocket, passo: float) -> List[str]:
        if rocket.invisivel:
            estava_invisivel = rocket.invisivel
            rocket.avancar_invisibilidade(passo)
            if estava_invisivel and not rocket.invisivel:
                origem = rocket.vertice_ultimo_ataque or rocket.vertice_atual
                rocket.vertice_atual = AlgoritmosGrafo.vertice_mais_distante(
                    self.regiao.grafo, origem, excluir=[origem])
                return [f"{rocket.nome} reapareceu em {rocket.vertice_atual}."]
            return []
        chegou, destino = self._avancar_movimento_treinador(rocket, passo)
        if destino is None:
            return []
        mensagens = ([f"{rocket.nome} chegou a {destino}."] if chegou else
                     [f"{rocket.nome} está em trânsito para {destino}."])
        if not chegou:
            return mensagens
        alvos = [t for t in self.regiao.treinadores_em(rocket.vertice_atual, rocket.id)
                 if not isinstance(t, MembroEquipeRocket) and (t.equipe or t.insignias)]
        if alvos and self.regiao.batalha_permitida_em(rocket.vertice_atual):
            resultado, mensagem = self.equipe_rocket_ataca(rocket, self.rng.choice(alvos))
            mensagens.append(mensagem)
            if resultado:
                mensagens.extend(resultado.log)
        return mensagens

    # ------------------------------------------------------------------ #
    # Captura
    # ------------------------------------------------------------------ #
    def capturar(self, treinador: Treinador, pokemon_treinador: Pokemon,
                 pokemon_selvagem: Pokemon,
                 seletor_ataque: Optional[SeletorAtaque] = None,
                 abandonar: bool = False,
                 decisor_abandono: Optional[DecisorAbandonoCaptura] = None,
                 seletor_excedente: Optional[SeletorExcedente] = None) -> ResultadoDuelo:
        if not self.regiao.batalha_permitida_em(treinador.vertice_atual):
            raise ValueError("Capturas são proibidas no PMC e no laboratório.")
        if pokemon_treinador not in treinador.equipe or not pokemon_treinador.esta_disponivel():
            raise ValueError("Escolha um Pokémon consciente que pertença ao treinador.")
        if pokemon_selvagem.id not in self.regiao.pokemons_selvagens:
            raise ValueError("O Pokémon informado não está disponível na região.")
        if pokemon_selvagem.id in treinador.selvagens_ocultos:
            raise ValueError("Esse Pokémon permanece escondido deste treinador.")
        if treinador.em_transito or pokemon_selvagem.em_transito:
            raise ValueError("Capturas só podem começar com todos parados no mesmo vértice.")
        if pokemon_selvagem.vertice_atual != treinador.vertice_atual:
            raise ValueError("Treinador e Pokémon selvagem devem estar no mesmo vértice.")
        if treinador.pokebolas <= 0:
            raise ValueError("Não há Pokébolas disponíveis para a tentativa.")
        if (treinador.eh_jogador and not abandonar and decisor_abandono is None
                and seletor_ataque is None):
            raise ValueError("O jogador deve escolher manualmente o ataque da captura.")
        treinador.pokebolas -= 1
        resultado = SistemaBatalha.tentar_captura(
            treinador, pokemon_treinador, pokemon_selvagem,
            seletor_ataque=seletor_ataque, abandonar=abandonar,
            decisor_abandono=decisor_abandono, rng=self.rng)
        if resultado.abandonado:
            treinador.selvagens_ocultos.add(pokemon_selvagem.id)
        elif resultado.capturado:
            self.regiao.remover_pokemon_selvagem(pokemon_selvagem.id)
            if len(treinador.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
                resultado.log.append(treinador.adicionar_pokemon(pokemon_selvagem))
            elif seletor_excedente:
                escolhido = seletor_excedente(
                    treinador, treinador.equipe + [pokemon_selvagem])
                resultado.log.append(
                    treinador.adicionar_pokemon(pokemon_selvagem, escolhido))
            else:
                treinador.colocar_pokemon_pendente(pokemon_selvagem)
                resultado.log.append("Captura concluída; escolha manualmente o excedente.")
        treinador.tempo_decorrido += 1.0
        self._atualizar_status_prazo(treinador)
        self.avancar_mundo(1.0)
        for linha in resultado.log:
            self.regiao.registrar_log(linha)
        return resultado

    # ------------------------------------------------------------------ #
    # Batalha entre treinadores
    # ------------------------------------------------------------------ #
    def desafiar_treinador(
            self, desafiante: Treinador, desafiado: Treinador,
            escolha_desafiante: List[Pokemon], escolha_desafiado: List[Pokemon],
            aceitou: bool = True,
            seletor_ataque_desafiante: Optional[SeletorAtaque] = None,
            seletor_ataque_desafiado: Optional[SeletorAtaque] = None,
            seletor_substituto_desafiante: Optional[SeletorSubstituto] = None,
            seletor_substituto_desafiado: Optional[SeletorSubstituto] = None,
            decisor_desistencia_desafiado: Optional[DecisorDesistencia] = None
    ) -> ResultadoDuelo:
        if desafiante is desafiado:
            raise ValueError("Um treinador não pode desafiar a si mesmo.")
        if desafiante.em_transito or desafiado.em_transito:
            raise ValueError("Treinadores em trânsito não podem iniciar uma batalha.")
        if desafiante.vertice_atual != desafiado.vertice_atual:
            raise ValueError("Os treinadores precisam estar no mesmo vértice.")
        if not self.regiao.batalha_permitida_em(desafiante.vertice_atual):
            raise ValueError("Batalhas são proibidas no PMC e no laboratório.")
        resultado = SistemaBatalha.batalha_treinadores(
            desafiante, desafiado, escolha_desafiante, escolha_desafiado,
            aceitou=aceitou,
            seletor_ataque_desafiante=seletor_ataque_desafiante,
            seletor_ataque_desafiado=seletor_ataque_desafiado,
            seletor_substituto_desafiante=seletor_substituto_desafiante,
            seletor_substituto_desafiado=seletor_substituto_desafiado,
            decisor_desistencia_desafiado=decisor_desistencia_desafiado,
            rng=self.rng)
        if not resultado.recusado:
            self.avancar_mundo(1.0)
            self._atualizar_status_prazo(desafiante)
            self._atualizar_status_prazo(desafiado)
        if (isinstance(desafiado, LiderGinasio) and
                resultado.vencedor_treinador is desafiante):
            desafiante.conquistar_insignia(desafiado.id_insignia)
            resultado.log.append(
                f"{desafiante.nome} conquistou a insígnia {desafiado.id_insignia}!")
        for linha in resultado.log:
            self.regiao.registrar_log(linha)
        return resultado

    # ------------------------------------------------------------------ #
    # Equipe Rocket
    # ------------------------------------------------------------------ #
    def equipe_rocket_ataca(self, rocket: MembroEquipeRocket,
                            alvo: Treinador) -> Tuple[Optional[ResultadoDuelo], str]:
        if rocket.vertice_atual != alvo.vertice_atual:
            raise ValueError("A Equipe Rocket e o alvo devem estar no mesmo vértice.")
        if rocket.em_transito or alvo.em_transito:
            raise ValueError("A Equipe Rocket só pode atacar após chegar ao vértice.")
        rocket_pk = next((p for p in rocket.equipe if p.esta_disponivel()), None)
        alvo_pk = next((p for p in alvo.equipe if p.esta_disponivel()), None)
        if rocket_pk is None or alvo_pk is None:
            return None, f"{rocket.nome} não encontrou Pokémon disponíveis para o duelo."
        resultado = ResultadoDuelo()
        bloqueio_tecnico = False
        while rocket_pk.esta_disponivel() and alvo_pk.esta_disponivel():
            hp_antes = rocket_pk.hp + alvo_pk.hp
            ataque_alvo = SistemaBatalha.ataque_padrao(alvo, alvo_pk, rocket_pk)
            if SistemaBatalha.duelo(
                    alvo_pk, rocket_pk, ataque_alvo, alvo.xp, rocket.xp,
                    self.rng, resultado.log):
                break
            ataque_rocket = SistemaBatalha.ataque_padrao(rocket, rocket_pk, alvo_pk)
            if SistemaBatalha.duelo(
                    rocket_pk, alvo_pk, ataque_rocket, rocket.xp, alvo.xp,
                    self.rng, resultado.log):
                break
            if (rocket_pk.hp + alvo_pk.hp == hp_antes
                    and SistemaBatalha.bloqueio_mutuo(
                        rocket_pk, alvo_pk, rocket.xp, alvo.xp)):
                bloqueio_tecnico = True
                resultado.log.append(
                    "A Equipe Rocket recuou por bloqueio técnico sem dano.")
                break
        vertice_ataque = rocket.vertice_atual
        if not alvo_pk.esta_disponivel() and not bloqueio_tecnico:
            resultado.vencedor = rocket_pk
            self._rocket_rouba(rocket, alvo, resultado)
            rocket.tornar_invisivel(self.rng.uniform(20, 50), vertice_ataque)
            mensagem = f"Equipe Rocket venceu o ataque em {vertice_ataque}."
        else:
            resultado.vencedor = alvo_pk
            rocket.cancelar_transito()
            rocket.vertice_atual = AlgoritmosGrafo.vertice_mais_distante(
                self.regiao.grafo, vertice_ataque, excluir=[vertice_ataque])
            mensagem = f"Equipe Rocket foi derrotada e enviada para {rocket.vertice_atual}."
        return resultado, mensagem

    def _rocket_rouba(self, rocket: MembroEquipeRocket, alvo: Treinador,
                      resultado: ResultadoDuelo):
        opcoes = []
        if alvo.equipe:
            opcoes.append("pokemon")
        if alvo.insignias:
            opcoes.append("insignia")
        if not opcoes:
            resultado.log.append(f"{alvo.nome} não tinha nada para ser roubado.")
            return
        if self.rng.choice(opcoes) == "pokemon":
            pokemon = self.rng.choice(alvo.equipe)
            alvo.equipe.remove(pokemon)
            if len(rocket.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
                rocket.adicionar_pokemon(pokemon)
            else:
                rocket.deposito_professor.append(pokemon)
            resultado.log.append(f"A Equipe Rocket roubou {pokemon.apelido}.")
        else:
            insignia = self.rng.choice(alvo.insignias)
            alvo.insignias.remove(insignia)
            resultado.log.append(f"A Equipe Rocket roubou a insígnia {insignia}.")

    # ------------------------------------------------------------------ #
    # PMC, itens e Liga
    # ------------------------------------------------------------------ #
    def tratar_no_pmc(self, treinador: Treinador) -> List[str]:
        if self.regiao.grafo.obter_vertice(treinador.vertice_atual).tipo != "pmc":
            raise ValueError("O treinador precisa estar em um PMC.")
        mensagens = []
        for pokemon in treinador.equipe:
            if pokemon.status == StatusPokemon.MUITO_MACHUCADO:
                pokemon.iniciar_tratamento_pmc(self.rng)
                mensagens.append(f"{pokemon.apelido} iniciou tratamento no PMC.")
        if not mensagens:
            mensagens.append("Nenhum Pokémon precisava de tratamento.")
        return mensagens

    def usar_erva(self, treinador: Treinador, item_erva: Erva) -> str:
        treinador.usar_erva_em_todos()
        item_erva.coletado = True
        self.regiao.remover_item(item_erva.id)
        return f"{treinador.nome} usou uma erva medicinal."

    def coletar_item(self, treinador: Treinador, item) -> str:
        if item.vertice_atual != treinador.vertice_atual:
            raise ValueError("O item precisa estar no mesmo vértice do treinador.")
        if isinstance(item, Ovo):
            if not treinador.adicionar_ovo(item):
                return "Não é possível carregar mais ovos."
            self.regiao.remover_item(item.id)
            return f"{treinador.nome} encontrou um ovo misterioso!"
        if isinstance(item, PokebolaExtra):
            treinador.pokebolas += 1
            item.coletado = True
            self.regiao.remover_item(item.id)
            return f"{treinador.nome} encontrou uma Pokébola (total: {treinador.pokebolas})."
        if isinstance(item, Erva):
            return self.usar_erva(treinador, item)
        raise ValueError("Item desconhecido.")

    def registrar_na_liga(self, treinador: Treinador) -> str:
        if self.regiao.grafo.obter_vertice(treinador.vertice_atual).tipo != "estadio":
            raise ValueError("O treinador precisa estar no estádio.")
        if treinador.tempo_decorrido > self.regiao.prazo_maximo_inscricao:
            treinador.inscrito_na_liga = False
            treinador.registrado_status = "fora_do_prazo"
            return f"{treinador.nome} chegou fora do prazo e está inapto para a Liga."
        total_ginasios = self.regiao.total_ginasios()
        if not treinador.apto_para_inscricao(total_ginasios):
            necessarias = treinador.numero_insignias_necessarias(total_ginasios)
            return (f"{treinador.nome} ainda não tem insígnias suficientes "
                    f"({len(treinador.insignias)}/{necessarias}).")
        treinador.registrado_status = "sucesso"
        treinador.inscrito_na_liga = True
        return f"{treinador.nome} se inscreveu com sucesso na Liga Pokémon!"

    def _atualizar_status_prazo(self, treinador: Treinador):
        """Marca a inaptidão assim que o prazo expira, sem depender de insígnias."""
        if (not treinador.inscrito_na_liga
                and treinador.tempo_decorrido > self.regiao.prazo_maximo_inscricao):
            treinador.registrado_status = "fora_do_prazo"
