"""Motor da simulação.

Integra a `Regiao`, o `Grafo`/`AlgoritmosGrafo` e o `SistemaBatalha`
e oferece uma API usada pela interface gráfica para: criar o jogador,
mover treinadores, avançar o mundo e resolver batalhas.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple

from models.grafo import AlgoritmosGrafo
from models.regiao import Regiao
from models.treinador import Treinador, LiderGinasio, MembroEquipeRocket
from models.pokemon import Pokemon
from models.item import Ovo, Erva, PokebolaExtra
from models.batalha import SistemaBatalha, ResultadoDuelo


class Simulacao:
    def __init__(self, regiao: Regiao, seed: Optional[int] = None):
        self.regiao = regiao
        self.rng = random.Random(seed)
        self.jogador: Optional[Treinador] = None

    # ------------------------------------------------------------------ #
    # Criação do jogador
    # ------------------------------------------------------------------ #
    def criar_jogador(self, nome: str, id_especie_inicial: Optional[str] = None) -> Treinador:
        """
        Cria o treinador controlado pelo jogador no vértice do laboratório.
        Se `id_especie_inicial` for informado (e for uma das 3 espécies
        oferecidas em [INICIAIS]), o jogador recebe apenas aquele pokémon.
        Caso contrário, recebe UM pokémon aleatório do laboratório (regra
        do enunciado para quem recusa os iniciais oferecidos).
        """
        jogador = Treinador(nome, self.regiao.vertice_laboratorio, eh_jogador=True)
        pokedex = self.regiao.pokedex

        especies_iniciais = [e for e in pokedex.todas() if e.fase == 1]
        # tenta restringir às 3 espécies clássicas (água/fogo/planta) se existirem
        tipos_classicos = {"agua", "fogo", "grama"}
        classicas = [e for e in especies_iniciais if set(e.tipos) & tipos_classicos]
        if classicas:
            especies_iniciais = classicas

        if id_especie_inicial and pokedex.existe(id_especie_inicial):
            especie = pokedex.obter(id_especie_inicial)
            pk = Pokemon(especie, pokedex, hp=100, xp=0.0, rng=self.rng)
            jogador.adicionar_pokemon(pk, self.rng)
        else:
            especie = self.rng.choice(especies_iniciais)
            pk = Pokemon(especie, pokedex, hp=100, xp=0.0, rng=self.rng)
            jogador.adicionar_pokemon(pk, self.rng)

        self.regiao.adicionar_treinador(jogador)
        self.jogador = jogador
        self.regiao.registrar_log(f"{nome} iniciou a jornada em {self.regiao.vertice_laboratorio} "
                                   f"com {pk.apelido}!")
        return jogador

    def especies_iniciais_disponiveis(self):
        pokedex = self.regiao.pokedex
        tipos_classicos = {"agua", "fogo", "grama"}
        candidatas = [e for e in pokedex.todas() if e.fase == 1 and set(e.tipos) & tipos_classicos]
        return candidatas or [e for e in pokedex.todas() if e.fase == 1]

    # ------------------------------------------------------------------ #
    # Movimentação (Requisito Adicional 2 e 7: um vértice por vez)
    # ------------------------------------------------------------------ #
    def vizinhos_de(self, treinador: Treinador) -> List[Tuple[str, float]]:
        return self.regiao.grafo.vizinhos(treinador.vertice_atual)

    def calcular_rota(self, origem: str, destino: str) -> Tuple[List[str], float]:
        """Usa Dijkstra (implementado manualmente em models/grafo.py) para
        encontrar o caminho de menor custo entre dois vértices."""
        return AlgoritmosGrafo.caminho_minimo(self.regiao.grafo, origem, destino)

    def mover_um_passo(self, treinador: Treinador, vertice_destino: str) -> List[str]:
        """Move um treinador para um vértice VIZINHO (um passo), conforme a
        regra de que o movimento ocorre um vértice por vez."""
        vizinhos = dict(self.regiao.grafo.vizinhos(treinador.vertice_atual))
        if vertice_destino not in vizinhos:
            raise ValueError(f"{vertice_destino} não é adjacente a {treinador.vertice_atual}.")
        peso = vizinhos[vertice_destino]
        eventos_ovo = treinador.mover_para(vertice_destino, peso, self.rng)
        mensagens = [f"{treinador.nome} vai de {treinador.vertice_atual} para {vertice_destino} "
                     f"(custo {peso:g})."]
        mensagens.extend(self._processar_eventos_ovo(treinador, eventos_ovo))
        for msg in mensagens:
            self.regiao.registrar_log(msg)
        return mensagens

    def _processar_eventos_ovo(self, treinador: Treinador, eventos) -> List[str]:
        mensagens = []
        for tipo_evento, ovo in eventos:
            if tipo_evento == "ovo_chocou":
                especie = ovo.chocar()
                pokemon = Pokemon(especie, self.regiao.pokedex, hp=100, xp=0.0, rng=self.rng)
                treinador.ovos.remove(ovo)
                if len(treinador.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
                    msg = treinador.adicionar_pokemon(pokemon, self.rng)
                    mensagens.append(f"Um ovo chocou! {msg}")
                else:
                    treinador.deposito_professor.append(pokemon)
                    mensagens.append(f"Um ovo chocou e revelou {pokemon.apelido}, mas a equipe "
                                      f"estava cheia -- enviado ao Prof. Carvalho.")
        return mensagens

    # ------------------------------------------------------------------ #
    # Avanço do "mundo" (NPCs, patrulha, incubação de outros treinadores, etc.)
    # ------------------------------------------------------------------ #
    def avancar_mundo(self, passos: int = 1) -> List[str]:
        mensagens = []
        for _ in range(passos):
            self.regiao.tempo_global += 1.0
            for lider in self.regiao.lideres_ginasio():
                mensagens.extend(self._tick_lider_ginasio(lider))
            for comum in self.regiao.treinadores_comuns():
                if comum.eh_jogador:
                    continue
                mensagens.extend(self._tick_treinador_npc(comum))
            for rocket in self.regiao.membros_rocket():
                mensagens.extend(self._tick_rocket(rocket))
        for msg in mensagens:
            self.regiao.registrar_log(msg)
        return mensagens

    def _tick_lider_ginasio(self, lider: LiderGinasio) -> List[str]:
        if lider.fixo:
            return []
        msgs = []
        if lider.esta_no_ginasio() and not lider._patrulhando:
            lider._tempo_restante_fora -= 1
            if lider._tempo_restante_fora <= 0:
                lider._patrulhando = True
                lider._tempo_restante_fora = self.rng.uniform(15, 40)  # "distância" de patrulha
        elif lider._patrulhando:
            vizinhos = self.regiao.grafo.vizinhos(lider.vertice_atual)
            if vizinhos:
                destino, peso = self.rng.choice(vizinhos)
                lider.mover_para(destino, peso, self.rng)
                lider._tempo_restante_fora -= peso
                msgs.append(f"{lider.nome} (líder) foi avistado em {destino}.")
            if lider._tempo_restante_fora <= 0:
                lider._patrulhando = False  # começa a voltar ao ginásio
        else:
            # retornando ao ginásio pelo caminho mais curto (Dijkstra)
            caminho, _ = AlgoritmosGrafo.caminho_minimo(
                self.regiao.grafo, lider.vertice_atual, lider.vertice_ginasio)
            if len(caminho) >= 2:
                proximo = caminho[1]
                peso = dict(self.regiao.grafo.vizinhos(lider.vertice_atual))[proximo]
                lider.mover_para(proximo, peso, self.rng)
                if lider.esta_no_ginasio():
                    lider._tempo_restante_fora = lider.tempo_permanencia_no_ginasio
                    msgs.append(f"{lider.nome} retornou ao ginásio {lider.vertice_ginasio}.")
        return msgs

    def _tick_treinador_npc(self, treinador: Treinador) -> List[str]:
        if self.rng.random() > 0.6:
            return []  # nem todo NPC se move a cada passo (evita log excessivo)
        vizinhos = self.regiao.grafo.vizinhos(treinador.vertice_atual)
        if not vizinhos:
            return []
        destino, peso = self.rng.choice(vizinhos)
        eventos = treinador.mover_para(destino, peso, self.rng)
        return self._processar_eventos_ovo(treinador, eventos)

    def _tick_rocket(self, rocket: MembroEquipeRocket) -> List[str]:
        msgs = []
        if rocket.invisivel:
            rocket.avancar_invisibilidade(1.0)
            return msgs
        vizinhos = self.regiao.grafo.vizinhos(rocket.vertice_atual)
        if vizinhos and self.rng.random() < 0.6:
            destino, peso = self.rng.choice(vizinhos)
            rocket.mover_para(destino, peso, self.rng)

        # tenta um roubo oportunista se encontrar um treinador no mesmo vértice
        alvos = [t for t in self.regiao.treinadores_em(rocket.vertice_atual, excluir_id=rocket.id)
                 if not isinstance(t, MembroEquipeRocket) and not isinstance(t, LiderGinasio)
                 and (t.equipe or t.insignias)
                 and self.regiao.batalha_permitida_em(rocket.vertice_atual)]
        if alvos and self.rng.random() < 0.35:
            alvo = self.rng.choice(alvos)
            resultado, msg = self.equipe_rocket_ataca(rocket, alvo)
            msgs.append(msg)
            msgs.extend(resultado.log if resultado else [])
        return msgs

    # ------------------------------------------------------------------ #
    # Captura de pokémon selvagem
    # ------------------------------------------------------------------ #
    def capturar(self, treinador: Treinador, pokemon_treinador: Pokemon,
                 pokemon_selvagem: Pokemon) -> ResultadoDuelo:
        if not self.regiao.batalha_permitida_em(treinador.vertice_atual):
            raise ValueError("Batalhas (e capturas) são proibidas neste local (PMC/laboratório).")
        resultado = SistemaBatalha.tentar_captura(treinador, pokemon_treinador, pokemon_selvagem, self.rng)
        if resultado.capturado:
            self.regiao.remover_pokemon_selvagem(pokemon_selvagem.id)
            msg = treinador.adicionar_pokemon(pokemon_selvagem, self.rng)
            resultado.log.append(msg)
        for linha in resultado.log:
            self.regiao.registrar_log(linha)
        return resultado

    # ------------------------------------------------------------------ #
    # Batalha entre treinadores (inclui batalhas de ginásio)
    # ------------------------------------------------------------------ #
    def desafiar_treinador(self, desafiante: Treinador, desafiado: Treinador,
                            escolha_desafiante: List[Pokemon],
                            escolha_desafiado: List[Pokemon]) -> ResultadoDuelo:
        if not self.regiao.batalha_permitida_em(desafiante.vertice_atual):
            raise ValueError("Batalhas são proibidas neste local (PMC/laboratório).")
        if len(escolha_desafiante) < 1 or len(escolha_desafiado) < 1:
            raise ValueError("Cada lado precisa escolher ao menos 1 pokémon (o ideal são 3).")

        resultado = SistemaBatalha.batalha_treinadores(
            desafiante, desafiado, escolha_desafiante, escolha_desafiado, self.rng)

        if isinstance(desafiado, LiderGinasio) and resultado.vencedor is desafiante:
            desafiante.conquistar_insignia(desafiado.id_insignia)
            resultado.log.append(f"{desafiante.nome} conquistou a insígnia {desafiado.id_insignia}!")

        for linha in resultado.log:
            self.regiao.registrar_log(linha)
        return resultado

    # ------------------------------------------------------------------ #
    # Equipe Rocket: rouba pokémon/insígnia, exige vencer 1 duelo pokémon
    # ------------------------------------------------------------------ #
    def equipe_rocket_ataca(self, rocket: MembroEquipeRocket, alvo: Treinador) -> Tuple[Optional[ResultadoDuelo], str]:
        rocket_pk = next((p for p in rocket.equipe if p.esta_disponivel()), None)
        alvo_pk = next((p for p in alvo.equipe if p.esta_disponivel()), None)
        if rocket_pk is None or alvo_pk is None:
            return None, f"{rocket.nome} tentou atacar {alvo.nome}, mas não havia pokémons disponíveis."

        resultado = ResultadoDuelo()
        resultado.log.append(f"A Equipe Rocket ({rocket.nome}) emboscou {alvo.nome}! "
                              f"Duelo: {rocket_pk.apelido} vs {alvo_pk.apelido}.")
        for _ in range(30):
            if not alvo_pk.esta_disponivel() or not rocket_pk.esta_disponivel():
                break
            caido = SistemaBatalha.duelo(alvo_pk, rocket_pk, alvo.xp, rocket.xp, self.rng, resultado.log)
            if caido:
                break
            caido = SistemaBatalha.duelo(rocket_pk, alvo_pk, rocket.xp, alvo.xp, self.rng, resultado.log)
            if caido:
                break

        vertice_ataque = rocket.vertice_atual
        if not alvo_pk.esta_disponivel():
            resultado.vencedor = rocket_pk
            resultado.log.append(f"A Equipe Rocket venceu o duelo!")
            self._rocket_rouba(rocket, alvo, resultado)
            duracao_invisivel = self.rng.uniform(20, 50)
            rocket.tornar_invisivel(duracao_invisivel)
            resultado.log.append(f"{rocket.nome} foge e fica invisível por um tempo...")
            msg = f"Equipe Rocket ataca {alvo.nome} em {vertice_ataque} e VENCE!"
        else:
            resultado.vencedor = alvo_pk
            resultado.log.append(f"{alvo.nome} repeliu a Equipe Rocket!")
            destino = AlgoritmosGrafo.vertice_mais_distante(
                self.regiao.grafo, rocket.vertice_atual, excluir=[rocket.vertice_atual])
            rocket.vertice_atual = destino
            resultado.log.append(f"{rocket.nome} é enviado para longe, até {destino}.")
            msg = f"Equipe Rocket ataca {alvo.nome} em {vertice_ataque} e é derrotada!"

        return resultado, msg

    def _rocket_rouba(self, rocket: MembroEquipeRocket, alvo: Treinador, resultado: ResultadoDuelo):
        opcoes = []
        if alvo.equipe:
            opcoes.append("pokemon")
        if alvo.insignias:
            opcoes.append("insignia")
        if not opcoes:
            resultado.log.append(f"{alvo.nome} não tinha nada para ser roubado.")
            return
        escolha = self.rng.choice(opcoes)
        if escolha == "pokemon":
            pk = self.rng.choice(alvo.equipe)
            alvo.equipe.remove(pk)
            if len(rocket.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
                rocket.adicionar_pokemon(pk, self.rng)
            else:
                rocket.deposito_professor.append(pk)
            resultado.log.append(f"A Equipe Rocket roubou {pk.apelido} de {alvo.nome}!")
        else:
            insignia = self.rng.choice(alvo.insignias)
            alvo.insignias.remove(insignia)
            resultado.log.append(f"A Equipe Rocket roubou a insígnia {insignia} de {alvo.nome}!")

    # ------------------------------------------------------------------ #
    # PMC / erva
    # ------------------------------------------------------------------ #
    def tratar_no_pmc(self, treinador: Treinador) -> List[str]:
        vertice = self.regiao.grafo.obter_vertice(treinador.vertice_atual)
        if vertice.tipo != "pmc":
            raise ValueError("O treinador precisa estar em um PMC para usar esta ação.")
        msgs = []
        from models.pokemon import StatusPokemon
        for p in treinador.equipe:
            if p.status == StatusPokemon.MUITO_MACHUCADO:
                p.iniciar_tratamento_pmc(self.rng)
                msgs.append(f"{p.apelido} iniciou tratamento no PMC.")
        if not msgs:
            msgs.append("Nenhum pokémon precisava de tratamento no PMC.")
        for msg in msgs:
            self.regiao.registrar_log(msg)
        return msgs

    def usar_erva(self, treinador: Treinador, item_erva: Erva) -> str:
        treinador.usar_erva_em_todos()
        item_erva.coletado = True
        self.regiao.remover_item(item_erva.id)
        msg = f"{treinador.nome} usou uma erva medicinal (+10 HP a todos os pokémons conscientes)."
        self.regiao.registrar_log(msg)
        return msg

    def coletar_item(self, treinador: Treinador, item) -> str:
        if isinstance(item, Ovo):
            if not treinador.adicionar_ovo(item):
                return "Não é possível carregar mais ovos (limite de 7 entre equipe + ovos)."
            self.regiao.remover_item(item.id)
            return f"{treinador.nome} encontrou um ovo misterioso!"
        elif isinstance(item, PokebolaExtra):
            treinador.pokebolas_extras += 1
            item.coletado = True
            self.regiao.remover_item(item.id)
            return f"{treinador.nome} encontrou uma pokébola extra! (total: {treinador.pokebolas_extras})"
        elif isinstance(item, Erva):
            return self.usar_erva(treinador, item)
        return "Item desconhecido."

    # ------------------------------------------------------------------ #
    # Inscrição na Liga -- Requisito Adicional 6
    # ------------------------------------------------------------------ #
    def registrar_na_liga(self, treinador: Treinador) -> str:
        vertice = self.regiao.grafo.obter_vertice(treinador.vertice_atual)
        if vertice.tipo != "estadio":
            raise ValueError("O treinador precisa estar no estádio para se inscrever.")
        total_ginasios = self.regiao.total_ginasios()
        if not treinador.apto_para_inscricao(total_ginasios):
            necessarias = treinador.numero_insignias_necessarias(total_ginasios)
            return (f"{treinador.nome} ainda não tem insígnias suficientes "
                    f"({len(treinador.insignias)}/{necessarias}).")
        if treinador.distancia_percorrida > self.regiao.prazo_maximo_inscricao:
            treinador.registrado_status = "fora_do_prazo"
            msg = (f"{treinador.nome} chegou tarde demais! Prazo máximo era "
                   f"{self.regiao.prazo_maximo_inscricao:.0f}, mas já se passaram "
                   f"{treinador.distancia_percorrida:.0f} unidades. Inapto para a Liga.")
        else:
            treinador.registrado_status = "sucesso"
            treinador.inscrito_na_liga = True
            msg = (f"{treinador.nome} se inscreveu com sucesso na Liga Pokémon! "
                   f"({treinador.distancia_percorrida:.0f}/{self.regiao.prazo_maximo_inscricao:.0f} "
                   f"unidades de prazo utilizadas)")
        self.regiao.registrar_log(msg)
        return msg
