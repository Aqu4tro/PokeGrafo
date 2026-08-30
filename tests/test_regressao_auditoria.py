import random

import pytest

from engine.simulacao import Simulacao
from io_utils.carregador import ErroArquivoRegiao, carregar_regiao
from models.batalha import SistemaBatalha
from models.pokemon import Pokemon, StatusPokemon
from models.treinador import MembroEquipeRocket, Treinador


def novo_pokemon(regiao, *, especie="aguinha", ap=20, dp=20, hp=100, xp=0,
                 apelido=None):
    return Pokemon(
        regiao.pokedex.obter(especie), regiao.pokedex,
        ap_inicial=ap, dp_inicial=dp, hp=hp, xp=xp,
        apelido=apelido, rng=random.Random(1))


@pytest.mark.parametrize("tipo", ["npc", "rocket", "selvagem"])
def test_entidade_consume_exatamente_o_peso_antes_de_chegar(caminho_mapa, tipo):
    regiao = carregar_regiao(str(caminho_mapa), seed_extra=55)
    simulacao = Simulacao(regiao, seed=4)
    regiao.pokemons_selvagens.clear()
    if tipo == "npc":
        entidade = regiao.treinadores_comuns()[0]
        regiao.treinadores = {entidade.id: entidade}
    elif tipo == "rocket":
        entidade = regiao.membros_rocket()[0]
        regiao.treinadores = {entidade.id: entidade}
    else:
        regiao = carregar_regiao(str(caminho_mapa), seed_extra=55)
        simulacao = Simulacao(regiao, seed=4)
        entidade = next(iter(regiao.pokemons_selvagens.values()))
        regiao.treinadores.clear()
        regiao.pokemons_selvagens = {entidade.id: entidade}

    origem = entidade.vertice_atual
    simulacao.avancar_mundo(1)
    destino = entidade.transito_destino
    peso = entidade.transito_tempo_total

    assert entidade.vertice_atual == origem
    assert entidade.em_transito
    assert entidade.transito_tempo_restante == pytest.approx(peso - 1)
    if tipo == "selvagem":
        assert entidade not in regiao.pokemons_selvagens_em(origem)
    else:
        assert entidade not in regiao.treinadores_em(origem)

    simulacao.avancar_mundo(peso - 1)
    assert not entidade.em_transito
    assert entidade.vertice_atual == destino
    assert simulacao.regiao.tempo_global == pytest.approx(peso)


def test_dano_usa_exatamente_maximo_entre_zero_e_ap_menos_dp(regiao):
    atacante = novo_pokemon(regiao, ap=20, dp=10, xp=0)
    defensor = novo_pokemon(regiao, ap=10, dp=30, xp=0)
    ataque_com_poder_declarado = atacante.ataques[0]

    SistemaBatalha.duelo(
        atacante, defensor, ataque_com_poder_declarado,
        rng=random.Random(1))
    assert defensor.hp == 100  # poder do ataque não burla AP <= DP

    atacante.ap_inicial = 40
    SistemaBatalha.duelo(
        atacante, defensor, ataque_com_poder_declarado,
        rng=random.Random(1))
    assert defensor.hp == 90

    defensor.hp = 100
    atacante.ap_inicial = 20
    defensor.dp_inicial = 24
    SistemaBatalha.duelo(
        atacante, defensor, ataque_com_poder_declarado,
        bonus_xp_atacante=5, bonus_xp_defensor=0,
        rng=random.Random(1))
    assert defensor.hp == 99


def test_vitoria_contra_xp_maior_ou_igual_concede_bonus_exato_de_ap_dp(regiao):
    pokemon = novo_pokemon(regiao, ap=20, dp=30, xp=0)
    pokemon.registrar_vitoria_batalha(0, random.Random(1))
    assert pokemon.xp == 10
    assert pokemon.bonus_batalha_ap == 1
    assert pokemon.bonus_batalha_dp == 1
    assert pokemon.ap == pytest.approx(22)  # +1 do XP e +1 da vitória
    assert pokemon.dp == pytest.approx(32)

    sem_bonus = novo_pokemon(regiao, ap=20, dp=30, xp=5)
    sem_bonus.registrar_vitoria_batalha(4, random.Random(1))
    assert sem_bonus.bonus_batalha_ap == 0
    assert sem_bonus.bonus_batalha_dp == 0
    assert sem_bonus.ap == pytest.approx(21.5)
    assert sem_bonus.dp == pytest.approx(31.5)


def test_desistencia_no_meio_da_captura_preserva_hp(simulacao, jogador):
    jogador.vertice_atual = "v1"
    atacante = jogador.equipe[0]
    atacante.ap_inicial = 30
    atacante.dp_inicial = 10
    atacante.hp = 100
    atacante.xp = 0
    atacante._recalcular_status(random.Random(1))
    selvagem = novo_pokemon(
        simulacao.regiao, especie="pedrinha", ap=20, dp=10, hp=100, xp=0)
    simulacao.regiao.adicionar_pokemon_selvagem(selvagem, "v1")
    estados_observados = []

    def abandonar_no_segundo_turno(_treinador, turno, aliado, oponente):
        estados_observados.append((turno, aliado.hp, oponente.hp))
        return turno == 2

    resultado = simulacao.capturar(
        jogador, atacante, selvagem,
        seletor_ataque=lambda _t, pokemon, _d: pokemon.ataques[0],
        decisor_abandono=abandonar_no_segundo_turno)

    assert resultado.abandonado and not resultado.capturado
    assert resultado.turnos == 2
    assert estados_observados == [(1, 100, 100), (2, 90, 80)]
    assert atacante.hp == 90
    assert selvagem.hp == 80
    assert jogador.pokebolas == 6


def test_cem_turnos_parado_no_pmc_nao_contam_como_distancia(simulacao, jogador):
    simulacao.regiao.treinadores = {jogador.id: jogador}
    simulacao.regiao.pokemons_selvagens.clear()
    jogador.vertice_atual = "pmc1"
    xp_inicial = [pokemon.xp for pokemon in jogador.equipe]

    simulacao.avancar_mundo(100, treinador_parado=jogador)

    assert [pokemon.xp for pokemon in jogador.equipe] == xp_inicial
    assert jogador.distancia_percorrida == 0
    assert jogador.tempo_decorrido == 100


def test_prazo_vencido_sem_insignias_marca_inaptidao_imediatamente(simulacao, jogador):
    simulacao.regiao.treinadores = {jogador.id: jogador}
    simulacao.regiao.pokemons_selvagens.clear()
    jogador.vertice_atual = simulacao.regiao.vertices_estadio()[0]
    jogador.insignias.clear()
    jogador.tempo_decorrido = simulacao.regiao.prazo_maximo_inscricao

    simulacao.avancar_mundo(1, treinador_parado=jogador)
    assert jogador.registrado_status == "fora_do_prazo"

    mensagem = simulacao.registrar_na_liga(jogador)
    assert "inapto" in mensagem
    assert jogador.registrado_status == "fora_do_prazo"
    assert not jogador.inscrito_na_liga


def test_equipe_rocket_rouba_fica_invisivel_e_reaparece_distante(simulacao):
    regiao = simulacao.regiao
    regiao.pokemons_selvagens.clear()
    rocket = MembroEquipeRocket("Jessie", "v1")
    alvo = Treinador("Vítima", "v1")
    pokemon_rocket = novo_pokemon(regiao, ap=100, dp=100, hp=100, apelido="R")
    pokemon_alvo = novo_pokemon(regiao, ap=1, dp=1, hp=20, apelido="A")
    rocket.adicionar_pokemon(pokemon_rocket)
    alvo.adicionar_pokemon(pokemon_alvo)
    regiao.treinadores = {rocket.id: rocket, alvo.id: alvo}

    resultado, _ = simulacao.equipe_rocket_ataca(rocket, alvo)

    assert resultado.vencedor is pokemon_rocket
    assert pokemon_alvo not in alvo.equipe
    assert pokemon_alvo in rocket.equipe
    assert rocket.invisivel
    origem_roubo = rocket.vertice_ultimo_ataque
    esperado = simulacao.calcular_rota(
        origem_roubo,
        max(regiao.grafo.ids_vertices(),
            key=lambda vertice: simulacao.calcular_rota(origem_roubo, vertice)[1]))[0][-1]

    rocket._timer_invisivel = 1
    regiao.treinadores = {rocket.id: rocket}
    simulacao.avancar_mundo(1)
    assert not rocket.invisivel
    assert rocket.vertice_atual == esperado


def test_derrota_da_equipe_rocket_envia_ao_vertice_mais_distante(simulacao):
    regiao = simulacao.regiao
    regiao.pokemons_selvagens.clear()
    rocket = MembroEquipeRocket("James", "v1")
    alvo = Treinador("Defensor", "v1")
    pokemon_rocket = novo_pokemon(regiao, ap=1, dp=1, hp=20, apelido="R")
    pokemon_alvo = novo_pokemon(regiao, ap=100, dp=100, hp=100, apelido="D")
    rocket.adicionar_pokemon(pokemon_rocket)
    alvo.adicionar_pokemon(pokemon_alvo)
    regiao.treinadores = {rocket.id: rocket, alvo.id: alvo}

    resultado, _ = simulacao.equipe_rocket_ataca(rocket, alvo)

    distancias = {
        vertice: simulacao.calcular_rota("v1", vertice)[1]
        for vertice in regiao.grafo.ids_vertices()
        if vertice != "v1"
    }
    assert resultado.vencedor is pokemon_alvo
    assert rocket.vertice_atual == max(distancias, key=distancias.get)
    assert not rocket.invisivel


def mapa_minimo(prazo="20", aresta="lab;v1;2", evolucao=""):
    return f"""
[REGIAO]
nome = Teste
prazo_inscricao = {prazo}

[VERTICES]
lab;Laboratório;laboratorio;0;0
v1;Vila;normal;1;0

[ARESTAS]
{aresta}

[ESPECIES]
agua;Água;agua;1;;{evolucao}
fogo;Fogo;fogo;1;;
grama;Grama;grama;1;;

[INICIAIS]
agua
fogo
grama

[CONFIG]
num_treinadores_npc = 0
num_pokemons_selvagens = 0
num_itens_extras = 0
num_ervas = 0
num_ovos = 0
num_membros_rocket = 0
seed = 1
"""


@pytest.mark.parametrize("prazo", ["20", "30"])
def test_prazo_configurado_aceita_fronteiras_inclusivas(tmp_path, prazo):
    caminho = tmp_path / "mapa.txt"
    caminho.write_text(mapa_minimo(prazo=prazo), encoding="utf-8")
    regiao = carregar_regiao(str(caminho))
    assert regiao.prazo_maximo_inscricao == float(prazo)


@pytest.mark.parametrize("prazo", ["19.99", "30.01"])
def test_prazo_configurado_rejeita_valores_fora_do_intervalo(tmp_path, prazo):
    caminho = tmp_path / "mapa.txt"
    caminho.write_text(mapa_minimo(prazo=prazo), encoding="utf-8")
    with pytest.raises(ErroArquivoRegiao, match="fora do intervalo"):
        carregar_regiao(str(caminho))


@pytest.mark.parametrize(
    ("conteudo", "mensagem"),
    [
        (mapa_minimo(aresta="lab;inexistente;2"), "vértice inexistente"),
        (mapa_minimo(aresta="lab;v1;0"), "peso da aresta deve ser positivo"),
        (mapa_minimo(evolucao="inexistente"), "espécie inexistente"),
        (mapa_minimo(prazo="nunca"), "deve ser numérico"),
        (mapa_minimo().replace("num_ovos = 0", "num_ovos = -1"),
         "não pode ser negativa"),
    ],
    ids=[
        "aresta-referencia-inexistente",
        "peso-zero",
        "evolucao-inexistente",
        "prazo-nao-numerico",
        "quantidade-negativa",
    ],
)
def test_carregador_contem_mapas_invalidos(tmp_path, conteudo, mensagem):
    caminho = tmp_path / "invalido.txt"
    caminho.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ErroArquivoRegiao, match=mensagem):
        carregar_regiao(str(caminho))


def test_recuperacao_natural_e_erva_respeitam_os_tres_estados(simulacao):
    regiao = simulacao.regiao
    consciente = novo_pokemon(regiao, hp=50)
    consciente.tick(10, random.Random(1), distancia_percorrida=0)
    assert consciente.hp == 51
    consciente.usar_erva()
    assert consciente.hp == 61

    inconsciente = novo_pokemon(regiao, hp=10)
    inconsciente._timer_inconsciente = 10
    inconsciente.usar_erva()
    assert inconsciente.hp == 10
    inconsciente.tick(9, random.Random(1), distancia_percorrida=0)
    assert inconsciente.status == StatusPokemon.INCONSCIENTE
    inconsciente.tick(1, random.Random(1), distancia_percorrida=0)
    assert inconsciente.status == StatusPokemon.CONSCIENTE
    assert inconsciente.hp == 20

    grave = novo_pokemon(regiao, hp=3)
    grave.tick(100, random.Random(1), distancia_percorrida=100)
    grave.usar_erva()
    assert grave.hp == 3
    treinador = Treinador("Enfermeiro", "pmc1")
    treinador.adicionar_pokemon(grave)
    simulacao.tratar_no_pmc(treinador)
    grave._timer_pmc = 10
    grave.tick(5, random.Random(1), em_tratamento_estacionario=False)
    assert grave._timer_pmc == 10
    grave.tick(10, random.Random(1), em_tratamento_estacionario=True)
    assert grave.status == StatusPokemon.CONSCIENTE
    assert grave.hp == 100


def test_lider_cumpre_permanencia_patrulha_e_retorno_ponderado(simulacao):
    regiao = simulacao.regiao
    lider = next(lider for lider in regiao.lideres_ginasio() if not lider.fixo)
    regiao.treinadores = {lider.id: lider}
    regiao.pokemons_selvagens.clear()
    lider.cancelar_transito()
    lider.vertice_atual = lider.vertice_ginasio
    lider._patrulhando = False
    lider._retornando_ao_ginasio = False
    lider._tempo_restante_no_ginasio = 2

    simulacao.avancar_mundo(1)
    assert lider.esta_no_ginasio() and not lider._patrulhando
    simulacao.avancar_mundo(1)
    assert lider.esta_no_ginasio() and lider._patrulhando

    simulacao.avancar_mundo(1)
    destino_patrulha = lider.transito_destino
    peso_patrulha = lider.transito_tempo_total
    assert lider.esta_no_ginasio() and lider.em_transito
    simulacao.avancar_mundo(peso_patrulha - 1)
    assert lider.vertice_atual == destino_patrulha
    assert not lider.em_transito

    lider._tempo_restante_fora = 0
    simulacao.avancar_mundo(1)
    assert lider._retornando_ao_ginasio

    for _ in range(200):
        if (lider.esta_no_ginasio() and not lider.em_transito
                and not lider._retornando_ao_ginasio):
            break
        simulacao.avancar_mundo(1)
    else:
        pytest.fail("O líder não retornou ao ginásio dentro do limite de segurança.")

    assert lider._tempo_restante_no_ginasio == lider.tempo_permanencia_no_ginasio
    simulacao.avancar_mundo(lider.tempo_permanencia_no_ginasio - 1)
    assert lider.esta_no_ginasio() and not lider._patrulhando
    simulacao.avancar_mundo(1)
    assert lider._patrulhando
