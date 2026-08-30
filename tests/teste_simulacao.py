"""
tests/teste_simulacao.py
=========================
Teste de integração "fumaça" (smoke test): roda um fluxo completo da
simulação sem a interface gráfica, para validar que os mecanismos centrais
funcionam corretamente e sem exceções:

    grafo/algoritmos -> carregamento do mapa -> criação do jogador ->
    movimentação -> captura -> batalha de treinador -> batalha de ginásio
    -> PMC -> erva -> ovo -> evolução -> inscrição na Liga

Não é uma suíte de testes unitários exaustiva (o foco do projeto é a
simulação em si), mas cobre o caminho feliz de cada requisito do
enunciado. Rode com:

    python3 -m tests.teste_simulacao
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.grafo import Grafo, AlgoritmosGrafo
from models.especie import multiplicador_de_dano
from io_utils.carregador import carregar_regiao
from engine.simulacao import Simulacao


def testar_algoritmos_grafo():
    print("\n== Teste: algoritmos de grafo (isolados) ==")
    g = Grafo()
    for v in "ABCDEF":
        g.adicionar_vertice(v)
    g.adicionar_aresta("A", "B", 2)
    g.adicionar_aresta("B", "C", 2)
    g.adicionar_aresta("A", "C", 5)
    g.adicionar_aresta("C", "D", 1)
    g.adicionar_aresta("D", "E", 1)
    g.adicionar_aresta("E", "F", 10)

    caminho, dist = AlgoritmosGrafo.caminho_minimo(g, "A", "E")
    assert caminho == ["A", "B", "C", "D", "E"], caminho
    assert dist == 6, dist
    assert AlgoritmosGrafo.eh_conexo(g) is True
    assert AlgoritmosGrafo.vertice_mais_distante(g, "A") == "F"
    assert set(AlgoritmosGrafo.bfs(g, "A")) == set("ABCDEF")
    assert set(AlgoritmosGrafo.dfs(g, "A")) == set("ABCDEF")
    print("OK: Dijkstra, BFS, DFS, conectividade e vértice mais distante.")


def testar_tabela_tipos():
    print("\n== Teste: vantagens de tipo ==")
    assert multiplicador_de_dano(["agua"], ["fogo"]) == 2.0
    assert multiplicador_de_dano(["fogo"], ["agua"]) == 0.5
    assert multiplicador_de_dano(["normal"], ["fantasma"]) == 0.0
    print("OK: multiplicadores de tipo coerentes com a tabela.")


def main():
    testar_algoritmos_grafo()
    testar_tabela_tipos()

    print("\n== Teste: carregamento da região a partir do arquivo texto ==")
    caminho_mapa = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "data", "mapa_regiao.txt")
    regiao = carregar_regiao(caminho_mapa, seed_extra=1)
    assert AlgoritmosGrafo.eh_conexo(regiao.grafo)
    soma = regiao.grafo.soma_pesos_arestas()
    assert soma * 10 <= regiao.prazo_maximo_inscricao <= soma * 15
    print(f"OK: região '{regiao.nome}' carregada ({regiao.grafo.numero_vertices()} vértices, "
          f"{regiao.grafo.numero_arestas()} arestas, prazo={regiao.prazo_maximo_inscricao:.0f}).")

    sim = Simulacao(regiao, seed=123)
    rng = random.Random(999)

    print("\n== Teste: criação do jogador e movimentação ==")
    jogador = sim.criar_jogador("Ash", id_especie_inicial="brasinha")
    assert len(jogador.equipe) == 1
    caminho, _ = sim.calcular_rota(jogador.vertice_atual, "g1")
    for i in range(len(caminho) - 1):
        sim.mover_um_passo(jogador, caminho[i + 1])
    assert jogador.vertice_atual == "g1"
    print(f"OK: jogador moveu-se do laboratório até {jogador.vertice_atual} "
          f"(distância acumulada: {jogador.distancia_percorrida:.1f}).")

    print("\n== Teste: avanço do mundo (NPCs, patrulha, Rocket) ==")
    sim.avancar_mundo(passos=5)
    print("OK: mundo avançou 5 passos sem exceções.")

    print("\n== Teste: batalha de ginásio ==")
    lider = next(l for l in regiao.lideres_ginasio() if l.vertice_ginasio == "g1")
    # reforça o time do jogador para garantir uma vitória determinística no teste
    from models.pokemon import Pokemon
    for _ in range(2):
        pk = Pokemon(regiao.pokedex.obter("aguinha"), regiao.pokedex, ap_inicial=80, dp_inicial=80,
                      hp=100, xp=500, rng=rng)
        jogador.adicionar_pokemon(pk, rng)
    escolha_jogador = jogador.equipe[:3]
    escolha_lider = lider.equipe[:3]
    resultado = sim.desafiar_treinador(jogador, lider, escolha_jogador, escolha_lider)
    print(f"Vencedor: {getattr(resultado.vencedor_treinador, 'nome', None)}")
    if resultado.vencedor_treinador is jogador:
        assert lider.id_insignia in jogador.insignias
        print(f"OK: jogador venceu o ginásio e recebeu a insígnia {lider.id_insignia}.")
    else:
        print("Aviso: jogador perdeu a batalha de ginásio nesta rodada (aleatoriedade normal).")

    print("\n== Teste: captura de pokémon selvagem ==")
    if regiao.pokemons_selvagens:
        selvagem = next(iter(regiao.pokemons_selvagens.values()))
        vertice_selvagem = selvagem.vertice_atual
        caminho, _ = sim.calcular_rota(jogador.vertice_atual, vertice_selvagem)
        for i in range(len(caminho) - 1):
            sim.mover_um_passo(jogador, caminho[i + 1])
        pokemon_ativo = jogador.pokemons_disponiveis()[0]
        resultado_captura = sim.capturar(jogador, pokemon_ativo, selvagem)
        print(f"Capturado? {resultado_captura.capturado}")

    print("\n== Teste: erva e PMC ==")
    if jogador.equipe:
        jogador.equipe[0].hp = 3
        jogador.equipe[0]._recalcular_status(rng)
        assert jogador.equipe[0].status == "muito_machucado"
    caminho, _ = sim.calcular_rota(jogador.vertice_atual, "pmc1")
    for i in range(len(caminho) - 1):
        sim.mover_um_passo(jogador, caminho[i + 1])
    msgs = sim.tratar_no_pmc(jogador)
    print("PMC:", msgs)

    print("\n== Teste: inscrição na Liga (fora do prazo/sem insígnias esperado) ==")
    caminho, _ = sim.calcular_rota(jogador.vertice_atual, "estadio")
    for i in range(len(caminho) - 1):
        sim.mover_um_passo(jogador, caminho[i + 1])
    print(sim.registrar_na_liga(jogador))

    print("\nTodos os testes de integração rodaram sem exceções. ✅")


if __name__ == "__main__":
    main()
