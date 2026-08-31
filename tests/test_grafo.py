import pytest

from models.especie import multiplicador_de_dano
from models.grafo import AlgoritmosGrafo, Grafo, HeapMinimo


def criar_grafo():
    grafo = Grafo()
    for vertice in "ABCDEF":
        grafo.adicionar_vertice(vertice)
    for origem, destino, peso in [
        ("A", "B", 2), ("B", "C", 2), ("A", "C", 5),
        ("C", "D", 1), ("D", "E", 1), ("E", "F", 10),
    ]:
        grafo.adicionar_aresta(origem, destino, peso)
    return grafo


def test_dijkstra_reconstroi_menor_caminho():
    caminho, distancia = AlgoritmosGrafo.caminho_minimo(criar_grafo(), "A", "E")
    assert caminho == ["A", "B", "C", "D", "E"]
    assert distancia == 6


def test_bfs_dfs_conectividade_e_vertice_mais_distante():
    grafo = criar_grafo()
    assert set(AlgoritmosGrafo.bfs(grafo, "A")) == set("ABCDEF")
    assert set(AlgoritmosGrafo.dfs(grafo, "A")) == set("ABCDEF")
    assert AlgoritmosGrafo.eh_conexo(grafo)
    assert AlgoritmosGrafo.vertice_mais_distante(grafo, "A") == "F"


def test_grafo_desconexo_e_destino_inalcancavel():
    grafo = criar_grafo()
    grafo.adicionar_vertice("G")
    assert not AlgoritmosGrafo.eh_conexo(grafo)
    assert AlgoritmosGrafo.caminho_minimo(grafo, "A", "G") == ([], float("inf"))


def test_heap_minimo_mantem_ordem_e_rejeita_extracao_vazia():
    heap = HeapMinimo()
    for prioridade, item in [(3, "c"), (1, "a"), (2, "b")]:
        heap.inserir(prioridade, item)
    assert [heap.extrair_minimo()[1] for _ in range(3)] == ["a", "b", "c"]
    with pytest.raises(IndexError):
        heap.extrair_minimo()


def test_tabela_de_tipos():
    assert multiplicador_de_dano(["agua"], ["fogo"]) == 2.0
    assert multiplicador_de_dano(["fogo"], ["agua"]) == 0.5
    assert multiplicador_de_dano(["normal"], ["fantasma"]) == 0.0
