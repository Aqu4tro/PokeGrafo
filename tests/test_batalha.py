import random

import pytest

from engine.simulacao import Simulacao
from models.batalha import SistemaBatalha
from models.pokemon import Pokemon
from models.treinador import Treinador


def equipe(treinador, regiao, ap, dp, hp=100, prefixo="P"):
    treinador.equipe.clear()
    for indice, especie_id in enumerate(("aguinha", "brasinha", "folhinha")):
        pokemon = Pokemon(
            regiao.pokedex.obter(especie_id), regiao.pokedex,
            ap_inicial=ap, dp_inicial=dp, hp=hp, xp=0,
            apelido=f"{prefixo}{indice + 1}", rng=random.Random(indice))
        treinador.adicionar_pokemon(pokemon)
    return list(treinador.equipe)


def selecionar_investida(_treinador, atacante, _defensor):
    return atacante.ataques[0]


def selecionar_esforco(_treinador, atacante, _defensor):
    return atacante.ataques[-1]


def primeiro(_treinador, disponiveis):
    return disponiveis[0]


def preparar_dupla(simulacao, jogador, ap_jogador=100, ap_npc=1, hp=100):
    jogador.vertice_atual = "v1"
    time_jogador = equipe(jogador, simulacao.regiao, ap_jogador, 100, hp, "J")
    npc = Treinador("Blue", "v1")
    time_npc = equipe(npc, simulacao.regiao, ap_npc, 1, hp, "N")
    simulacao.regiao.adicionar_treinador(npc)
    return npc, time_jogador, time_npc


def test_motor_exige_mesmo_vertice_zona_valida_e_times_de_tres(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    npc.vertice_atual = "v2"
    with pytest.raises(ValueError, match="mesmo vértice"):
        simulacao.desafiar_treinador(jogador, npc, time_jogador, time_npc)
    npc.vertice_atual = jogador.vertice_atual = "pmc1"
    with pytest.raises(ValueError, match="proibidas"):
        simulacao.desafiar_treinador(jogador, npc, time_jogador, time_npc)
    npc.vertice_atual = jogador.vertice_atual = "v1"
    with pytest.raises(ValueError, match="exatamente três"):
        simulacao.desafiar_treinador(jogador, npc, time_jogador[:2], time_npc)


def test_motor_rejeita_pokemon_estrangeiro_e_ataque_desconhecido(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    time_invalido = [time_jogador[0], time_jogador[1], time_npc[0]]
    with pytest.raises(ValueError, match="pertencer"):
        simulacao.desafiar_treinador(jogador, npc, time_invalido, time_npc)
    from models.ataque import Ataque
    with pytest.raises(ValueError, match="não conhece"):
        SistemaBatalha.duelo(time_jogador[0], time_npc[0], Ataque("Inválido", 999))


def test_desafiado_pode_recusar_sem_consumir_tempo(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    resultado = simulacao.desafiar_treinador(
        jogador, npc, time_jogador, time_npc, aceitou=False)
    assert resultado.recusado
    assert resultado.vencedor_treinador is None
    assert jogador.tempo_decorrido == 0
    assert simulacao.regiao.tempo_global == 0


def test_desafiado_pode_desistir_e_desafiante_nao(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    resultado = simulacao.desafiar_treinador(
        jogador, npc, time_jogador, time_npc, aceitou=True,
        seletor_ataque_desafiante=selecionar_investida,
        seletor_substituto_desafiante=primeiro,
        decisor_desistencia_desafiado=lambda _t, turno: turno == 1)
    assert resultado.desistente is npc
    assert resultado.vencedor_treinador is jogador
    assert jogador.xp == 3


def test_batalha_bloqueada_termina_por_desistencia_tecnica_sem_dano(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(
        simulacao, jogador, ap_jogador=1, ap_npc=1, hp=20)
    escolhas = []

    def escolher(treinador, disponiveis):
        escolhas.append((treinador.id, disponiveis[0].id))
        return disponiveis[0]

    resultado = simulacao.desafiar_treinador(
        jogador, npc, time_jogador, time_npc, aceitou=True,
        seletor_ataque_desafiante=selecionar_esforco,
        seletor_ataque_desafiado=selecionar_esforco,
        seletor_substituto_desafiante=escolher)
    assert resultado.vencedor_treinador in (jogador, npc)
    assert resultado.turnos > 0
    assert resultado.desistente is npc
    assert len(escolhas) == 1  # seleção inicial; nenhum Pokémon foi derrubado artificialmente
    assert all(pokemon.hp == 20 for pokemon in time_jogador + time_npc)
    assert any("bloqueio técnico" in linha.lower() for linha in resultado.log)


def test_substituicao_apos_nocaute_continua_sendo_manual(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(
        simulacao, jogador, ap_jogador=1, ap_npc=100, hp=20)
    time_jogador[0].dp_inicial = 1
    for pokemon in time_jogador[1:]:
        pokemon.ap_inicial = 200
        pokemon.dp_inicial = 200
    escolhas = []

    def escolher(treinador, disponiveis):
        escolhas.append((treinador.id, disponiveis[0].id))
        return disponiveis[0]

    resultado = simulacao.desafiar_treinador(
        jogador, npc, time_jogador, time_npc, aceitou=True,
        seletor_ataque_desafiante=selecionar_investida,
        seletor_substituto_desafiante=escolher)
    assert resultado.vencedor_treinador is jogador
    assert len(escolhas) == 2  # seleção inicial e substituição após o nocaute
    assert escolhas[0][1] != escolhas[1][1]
    assert [pokemon.xp for pokemon in time_npc] == [13, 3, 3]
    assert [pokemon.xp for pokemon in time_jogador] == [3, 30, 0]


def test_xp_e_concedido_apenas_a_quem_participou_dos_duelos(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    resultado = simulacao.desafiar_treinador(
        jogador, npc, time_jogador, time_npc, aceitou=True,
        seletor_ataque_desafiante=selecionar_investida,
        seletor_substituto_desafiante=primeiro)
    assert resultado.vencedor_treinador is jogador
    assert time_jogador[0].xp == 30
    assert time_jogador[1].xp == 0
    assert time_jogador[2].xp == 0
    assert [pokemon.xp for pokemon in time_npc] == [3, 3, 3]


def test_jogador_deve_fornecer_escolhas_manuais(simulacao, jogador):
    npc, time_jogador, time_npc = preparar_dupla(simulacao, jogador)
    with pytest.raises(ValueError, match="escolher seus ataques"):
        simulacao.desafiar_treinador(
            jogador, npc, time_jogador, time_npc, aceitou=True,
            seletor_substituto_desafiante=primeiro)
