import random

import pytest

from engine.simulacao import Simulacao
from io_utils.carregador import carregar_regiao
from models.item import Ovo
from models.pokemon import Pokemon, StatusPokemon
from models.treinador import Treinador


def test_jogador_aceita_tres_iniciais_distintos_e_sete_pokebolas(simulacao):
    jogador = simulacao.criar_jogador("Ash", aceitar_tres_iniciais=True)
    assert len(jogador.equipe) == 3
    assert {p.tipos[0] for p in jogador.equipe} == {"agua", "fogo", "grama"}
    assert len({p.especie.id for p in jogador.equipe}) == 3
    assert jogador.pokebolas == 7


def test_jogador_recusa_iniciais_e_recebe_um_aleatorio(regiao):
    jogador = Simulacao(regiao, seed=7).criar_jogador(
        "Misty", aceitar_tres_iniciais=False)
    assert len(jogador.equipe) == 1
    assert jogador.equipe[0].fase == 1
    assert jogador.pokebolas == 7


def preparar_captura(simulacao, jogador, hp_selvagem=20):
    destino = "v1"
    jogador.vertice_atual = destino
    atacante = jogador.equipe[0]
    atacante.ap_inicial = 100
    atacante.dp_inicial = 100
    selvagem = Pokemon(
        simulacao.regiao.pokedex.obter("pedrinha"), simulacao.regiao.pokedex,
        ap_inicial=1, dp_inicial=1, hp=hp_selvagem, xp=0,
        rng=random.Random(1))
    simulacao.regiao.adicionar_pokemon_selvagem(selvagem, destino)
    return atacante, selvagem


def test_captura_consumindo_pokebola_e_alterando_estado(simulacao, jogador):
    atacante, selvagem = preparar_captura(simulacao, jogador)
    resultado = simulacao.capturar(
        jogador, atacante, selvagem,
        seletor_ataque=lambda _t, pokemon, _d: pokemon.ataques[0])
    assert resultado.capturado
    assert jogador.pokebolas == 6
    assert selvagem in jogador.equipe
    assert selvagem.id not in simulacao.regiao.pokemons_selvagens
    assert jogador.xp == 3
    assert atacante.xp == 3


def test_captura_sem_pokebola_e_fora_do_vertice_sao_bloqueadas(simulacao, jogador):
    atacante, selvagem = preparar_captura(simulacao, jogador)
    jogador.pokebolas = 0
    with pytest.raises(ValueError, match="Pokébolas"):
        simulacao.capturar(jogador, atacante, selvagem)
    jogador.pokebolas = 1
    selvagem.vertice_atual = "v2"
    with pytest.raises(ValueError, match="mesmo vértice"):
        simulacao.capturar(jogador, atacante, selvagem)
    assert jogador.pokebolas == 1


def test_captura_do_jogador_exige_selecao_manual_de_ataque(simulacao, jogador):
    atacante, selvagem = preparar_captura(simulacao, jogador)
    with pytest.raises(ValueError, match="escolher manualmente"):
        simulacao.capturar(jogador, atacante, selvagem)
    assert jogador.pokebolas == 7


def test_abandono_consume_pokebola_e_esconde_selvagem(simulacao, jogador):
    atacante, selvagem = preparar_captura(simulacao, jogador)
    resultado = simulacao.capturar(jogador, atacante, selvagem, abandonar=True)
    assert resultado.abandonado and not resultado.capturado
    assert jogador.pokebolas == 6
    assert selvagem.id in jogador.selvagens_ocultos
    assert selvagem not in simulacao.regiao.pokemons_selvagens_em("v1", jogador)
    with pytest.raises(ValueError, match="escondido"):
        simulacao.capturar(jogador, atacante, selvagem)


def test_excedente_exige_escolha_manual_e_respeita_limite(simulacao, jogador):
    especie = simulacao.regiao.pokedex.obter("voltinho")
    while len(jogador.equipe) < Treinador.MAX_POKEMONS_ATIVOS:
        jogador.adicionar_pokemon(Pokemon(especie, simulacao.regiao.pokedex, rng=random.Random(2)))
    novo = Pokemon(especie, simulacao.regiao.pokedex, apelido="Novo", rng=random.Random(3))
    with pytest.raises(ValueError, match="Escolha manualmente"):
        jogador.adicionar_pokemon(novo)
    assert len(jogador.equipe) == 6
    escolhido = jogador.equipe[1]
    jogador.adicionar_pokemon(novo, escolhido)
    assert len(jogador.equipe) == 6
    assert novo in jogador.equipe
    assert escolhido in jogador.deposito_professor


def test_pokemon_pendente_conta_no_limite_total_com_ovos(simulacao, jogador):
    especie = simulacao.regiao.pokedex.obter("voltinho")
    while len(jogador.equipe) < 6:
        jogador.adicionar_pokemon(Pokemon(especie, simulacao.regiao.pokedex))
    pendente = Pokemon(especie, simulacao.regiao.pokedex)
    jogador.colocar_pokemon_pendente(pendente)
    ovo = Ovo(jogador.vertice_atual, especie)
    assert not jogador.adicionar_ovo(ovo)


def test_ovo_eclode_exatamente_em_cem_unidades(simulacao, jogador):
    ovo = Ovo(jogador.vertice_atual, simulacao.regiao.pokedex.obter("aguinha"), random.Random(1))
    assert jogador.adicionar_ovo(ovo)
    assert jogador.mover_para("v1", 99, random.Random(1)) == []
    eventos = jogador.mover_para("v2", 1, random.Random(1))
    assert eventos == [("ovo_chocou", ovo)]
    mensagens = simulacao._processar_eventos_ovo(jogador, eventos, None)
    assert len(jogador.ovos) == 0
    assert len(jogador.equipe) == 4
    assert any("ovo chocou" in mensagem.lower() for mensagem in mensagens)


def test_evolucao_aumenta_ap_e_dp_exatamente_trinta_por_cento(regiao):
    pokemon = Pokemon(
        regiao.pokedex.obter("aguinha"), regiao.pokedex,
        ap_inicial=20, dp_inicial=30, xp=990, rng=random.Random(1))
    ap_antes_evolucao = pokemon.ap_inicial + 0.10 * 1000
    dp_antes_evolucao = pokemon.dp_inicial + 0.10 * 1000
    pokemon.ganhar_xp(10, random.Random(1))
    assert pokemon.especie.id == "aguario"
    assert pokemon.ap == pytest.approx(ap_antes_evolucao * 1.30)
    assert pokemon.dp == pytest.approx(dp_antes_evolucao * 1.30)


def test_tratamento_pmc_pausa_ao_caminhar_e_avanca_parado(simulacao, jogador):
    jogador.vertice_atual = "pmc1"
    pokemon = jogador.equipe[0]
    pokemon.hp = 3
    pokemon._recalcular_status(random.Random(1))
    simulacao.tratar_no_pmc(jogador)
    timer_inicial = pokemon._timer_pmc
    jogador.mover_para("v4", 5, random.Random(1))
    assert pokemon.status == StatusPokemon.NO_PMC
    assert pokemon._timer_pmc == timer_inicial
    jogador.vertice_atual = "pmc1"
    jogador.avancar_parado(timer_inicial, em_pmc=True, rng=random.Random(1))
    assert pokemon.status == StatusPokemon.CONSCIENTE
    assert pokemon.hp == 100


def test_movimento_do_jogador_sincroniza_relogio_global(simulacao, jogador):
    origem = jogador.vertice_atual
    destino, peso = simulacao.regiao.grafo.vizinhos(origem)[0]
    simulacao.mover_um_passo(jogador, destino)
    assert simulacao.regiao.tempo_global == peso
    assert jogador.tempo_decorrido == peso
    assert jogador.distancia_percorrida == peso


def test_npc_rocket_e_selvagem_iniciam_transito_sem_teletransporte(caminho_mapa):
    for tipo in ("npc", "rocket", "selvagem"):
        regiao = carregar_regiao(str(caminho_mapa), seed_extra=55)
        simulacao = Simulacao(regiao, seed=4)
        if tipo == "npc":
            entidade = regiao.treinadores_comuns()[0]
            regiao.treinadores = {entidade.id: entidade}
        elif tipo == "rocket":
            entidade = regiao.membros_rocket()[0]
            regiao.treinadores = {entidade.id: entidade}
        else:
            entidade = next(iter(regiao.pokemons_selvagens.values()))
            regiao.treinadores = {}
            regiao.pokemons_selvagens = {entidade.id: entidade}
        origem = entidade.vertice_atual
        vizinhos = {v for v, _ in regiao.grafo.vizinhos(origem)}
        simulacao.avancar_mundo(1)
        assert entidade.vertice_atual == origem
        assert entidade.em_transito
        assert entidade.transito_destino in vizinhos
        assert entidade.transito_tempo_restante == (
            entidade.transito_tempo_total - 1)


def test_prazo_automatico_e_fronteiras_de_inscricao(caminho_mapa):
    regiao = carregar_regiao(str(caminho_mapa), seed_extra=1)
    soma = regiao.grafo.soma_pesos_arestas()
    assert soma * 10 <= regiao.prazo_maximo_inscricao <= soma * 15
    simulacao = Simulacao(regiao, seed=1)
    jogador = simulacao.criar_jogador("Red")
    jogador.vertice_atual = regiao.vertices_estadio()[0]
    jogador.insignias = [lider.id_insignia for lider in regiao.lideres_ginasio()]
    jogador.tempo_decorrido = regiao.prazo_maximo_inscricao
    assert "sucesso" in simulacao.registrar_na_liga(jogador)
    jogador.inscrito_na_liga = False
    jogador.tempo_decorrido = regiao.prazo_maximo_inscricao + 0.001
    assert "fora do prazo" in simulacao.registrar_na_liga(jogador)
    assert not jogador.inscrito_na_liga
