"""
models/grafo.py
================
Representação de grafo ponderado e não-direcionado e os algoritmos de grafo
usados pela simulação.

A estrutura de dados do grafo (lista de adjacência) e todos os algoritmos 
— busca em largura (BFS), busca em profundidade (DFS), teste de conectividade, 
e o algoritmo de Dijkstra (incluindo a fila de prioridade / heap mínimo 
que ele usa) — são
implementados manualmente neste arquivo, usando apenas listas, dicionários
e tuplas nativas do Python.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Iterable


class Vertice:
    """Um ponto (local) do mapa da região."""

    TIPOS_VALIDOS = {"normal", "ginasio", "pmc", "estadio", "laboratorio"}

    def __init__(self, id_vertice: str, nome: Optional[str] = None,
                 tipo: str = "normal", x: float = 0.0, y: float = 0.0):
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo de vértice inválido: {tipo!r}")
        self.id = id_vertice
        self.nome = nome or id_vertice
        self.tipo = tipo  # normal | ginasio | pmc | estadio | laboratorio
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Vertice({self.id!r}, tipo={self.tipo!r})"


class Grafo:
    """
    Grafo ponderado e não-direcionado, representado por lista de adjacência.

    A escolha de lista de adjacência (em vez de matriz de adjacência) é
    proposital: o mapa da região tende a ser esparso (cada ponto se conecta
    a poucos vizinhos), então a lista de adjacência oferece O(V+E) de espaço
    e permite que o Dijkstra rode em O((V+E) log V) com o heap manual abaixo,
    em vez de O(V^2) que uma matriz de adjacência exigiria.
    """

    def __init__(self):
        self._vertices: Dict[str, Vertice] = {}
        self._adj: Dict[str, List[Tuple[str, float]]] = {}

    # ---------------------------------------------------------------- #
    # Construção do grafo
    # ---------------------------------------------------------------- #
    def adicionar_vertice(self, id_vertice: str, nome: Optional[str] = None,
                           tipo: str = "normal", x: float = 0.0, y: float = 0.0) -> Vertice:
        if id_vertice in self._vertices:
            return self._vertices[id_vertice]
        v = Vertice(id_vertice, nome, tipo, x, y)
        self._vertices[id_vertice] = v
        self._adj[id_vertice] = []
        return v

    def adicionar_aresta(self, origem: str, destino: str, peso: float):
        if origem not in self._vertices or destino not in self._vertices:
            raise KeyError("Ambos os vértices da aresta precisam existir no grafo.")
        if peso < 0:
            raise ValueError("Este projeto não trabalha com pesos negativos (tempo de percurso).")
        # não-direcionado: aresta nos dois sentidos com o mesmo peso
        self._adj[origem].append((destino, peso))
        if origem != destino:
            self._adj[destino].append((origem, peso))

    # ---------------------------------------------------------------- #
    # Consultas
    # ---------------------------------------------------------------- #
    def vizinhos(self, id_vertice: str) -> List[Tuple[str, float]]:
        return self._adj.get(id_vertice, [])

    def vertices(self) -> Iterable[Vertice]:
        return self._vertices.values()

    def ids_vertices(self) -> List[str]:
        return list(self._vertices.keys())

    def existe_vertice(self, id_vertice: str) -> bool:
        return id_vertice in self._vertices

    def obter_vertice(self, id_vertice: str) -> Vertice:
        return self._vertices[id_vertice]

    def vertices_por_tipo(self, tipo: str) -> List[Vertice]:
        return [v for v in self._vertices.values() if v.tipo == tipo]

    def numero_vertices(self) -> int:
        return len(self._vertices)

    def numero_arestas(self) -> int:
        return sum(len(v) for v in self._adj.values()) // 2

    def soma_pesos_arestas(self) -> float:
        """Soma de todos os pesos das arestas (cada aresta contada 1 vez).
        Usada para calcular o prazo máximo de inscrição na Liga (10x a 15x
        essa soma, conforme o Requisito Adicional 6)."""
        total = 0.0
        vistos = set()
        for origem, lista in self._adj.items():
            for destino, peso in lista:
                chave = tuple(sorted((origem, destino)))
                if chave in vistos:
                    continue
                vistos.add(chave)
                total += peso
        return total

    def vertice_aleatorio(self, rng, apenas_tipo: Optional[str] = None) -> str:
        """Sorteia um id de vértice (opcionalmente restrito a um tipo)."""
        candidatos = self.ids_vertices() if apenas_tipo is None \
            else [v.id for v in self.vertices_por_tipo(apenas_tipo)]
        if not candidatos:
            candidatos = self.ids_vertices()
        return rng.choice(candidatos)


# ---------------------------------------------------------------------- #
# Heap mínimo (fila de prioridade) implementado manualmente
# ---------------------------------------------------------------------- #
class HeapMinimo:
    """
    Heap de mínimo (min-heap binário) implementado com uma lista Python
    "crua", sem usar o módulo `heapq`. Serve de fila de prioridade para o
    algoritmo de Dijkstra abaixo.

    Cada elemento inserido é a tupla (prioridade, sequência, item); o campo
    `sequência` garante desempate estável e evita comparar `item`
    diretamente quando as prioridades empatam.
    """

    def __init__(self):
        self._dados: List[Tuple[float, int, object]] = []
        self._seq = 0

    def vazio(self) -> bool:
        return len(self._dados) == 0

    def __len__(self):
        return len(self._dados)

    def inserir(self, prioridade: float, item: object):
        self._seq += 1
        self._dados.append((prioridade, self._seq, item))
        self._flutuar(len(self._dados) - 1)

    def extrair_minimo(self) -> Tuple[float, object]:
        if not self._dados:
            raise IndexError("HeapMinimo vazio")
        raiz = self._dados[0]
        ultimo = self._dados.pop()
        if self._dados:
            self._dados[0] = ultimo
            self._afundar(0)
        return raiz[0], raiz[2]

    # -- operações internas de manutenção do heap -- #
    def _flutuar(self, i: int):
        while i > 0:
            pai = (i - 1) // 2
            if self._dados[i][0] < self._dados[pai][0] or \
               (self._dados[i][0] == self._dados[pai][0] and self._dados[i][1] < self._dados[pai][1]):
                self._dados[i], self._dados[pai] = self._dados[pai], self._dados[i]
                i = pai
            else:
                break

    def _afundar(self, i: int):
        n = len(self._dados)
        while True:
            esq, dire = 2 * i + 1, 2 * i + 2
            menor = i
            if esq < n and self._chave(esq) < self._chave(menor):
                menor = esq
            if dire < n and self._chave(dire) < self._chave(menor):
                menor = dire
            if menor == i:
                break
            self._dados[i], self._dados[menor] = self._dados[menor], self._dados[i]
            i = menor

    def _chave(self, i: int):
        return self._dados[i][0], self._dados[i][1]


# ---------------------------------------------------------------------- #
# Algoritmos de grafo
# ---------------------------------------------------------------------- #
class AlgoritmosGrafo:
    """Implementações manuais dos algoritmos de grafo usados na simulação."""

    # ---------------- Dijkstra (caminho mínimo) ---------------- #
    @staticmethod
    def dijkstra(grafo: Grafo, origem: str) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
        """
        Calcula a distância mínima da origem a todos os vértices alcançáveis.

        Complexidade: O((V + E) log V), usando o HeapMinimo acima como fila
        de prioridade (cada aresta pode gerar no máximo uma inserção no
        heap, e cada extração custa O(log V)).

        Retorna (dist, pred):
            dist[v] = menor distância conhecida de `origem` até `v`
            pred[v] = vértice anterior a `v` no caminho mínimo (ou None)
        """
        dist: Dict[str, float] = {v.id: float("inf") for v in grafo.vertices()}
        pred: Dict[str, Optional[str]] = {v.id: None for v in grafo.vertices()}
        if origem not in dist:
            raise KeyError(f"Vértice de origem inexistente: {origem}")
        dist[origem] = 0.0

        heap = HeapMinimo()
        heap.inserir(0.0, origem)
        finalizados = set()

        while not heap.vazio():
            d_atual, u = heap.extrair_minimo()
            if u in finalizados:
                continue  # entrada obsoleta (lazy deletion)
            finalizados.add(u)

            for vizinho, peso in grafo.vizinhos(u):
                nova_dist = d_atual + peso
                # print(f"testando o vizinho {vizinho} a partir de {u} com nova_dist {nova_dist}")
                if nova_dist < dist[vizinho]:
                    dist[vizinho] = nova_dist
                    pred[vizinho] = u
                    heap.inserir(nova_dist, vizinho)

        return dist, pred

    @staticmethod
    def reconstruir_caminho(pred: Dict[str, Optional[str]], origem: str, destino: str) -> List[str]:
        if origem == destino:
            return [origem]
        if pred.get(destino) is None:
            return []
        caminho = [destino]
        atual = destino
        while atual != origem:
            atual = pred.get(atual)
            if atual is None:
                return []
            caminho.append(atual)
        caminho.reverse()
        return caminho

    @staticmethod
    def caminho_minimo(grafo: Grafo, origem: str, destino: str) -> Tuple[List[str], float]:
        """Atalho: roda Dijkstra e já devolve (caminho, distância_total)."""
        dist, pred = AlgoritmosGrafo.dijkstra(grafo, origem)
        d = dist.get(destino, float("inf"))
        if d == float("inf"):
            return [], float("inf")
        return AlgoritmosGrafo.reconstruir_caminho(pred, origem, destino), d

    # ---------------- Busca em largura (BFS) ---------------- #
    @staticmethod
    def bfs(grafo: Grafo, origem: str) -> List[str]:
        """
        Busca em largura manual (fila implementada com lista + índice,
        sem `collections.deque`). Retorna a ordem de visitação a partir de
        `origem`. Complexidade O(V + E).
        """
        if not grafo.existe_vertice(origem):
            raise KeyError(f"Vértice de origem inexistente: {origem}")
        visitados = {origem}
        ordem = [origem]
        fila = [origem]
        cabeca = 0
        while cabeca < len(fila):
            u = fila[cabeca]
            cabeca += 1
            for vizinho, _ in grafo.vizinhos(u):
                if vizinho not in visitados:
                    # TODO: se pá dá pra melhorar isso aqui não usando set pra visitados
                    visitados.add(vizinho)
                    ordem.append(vizinho)
                    fila.append(vizinho)
        return ordem

    @staticmethod
    def distancias_em_saltos(grafo: Grafo, origem: str) -> Dict[str, int]:
        """Número mínimo de arestas (saltos, não peso) da origem a cada vértice."""
        dist = {origem: 0}
        fila = [origem]
        cabeca = 0
        while cabeca < len(fila):
            u = fila[cabeca]
            cabeca += 1
            for vizinho, _ in grafo.vizinhos(u):
                if vizinho not in dist:
                    dist[vizinho] = dist[u] + 1
                    fila.append(vizinho)
        return dist

    # ---------------- Busca em profundidade (DFS) ---------------- #
    @staticmethod
    def dfs(grafo: Grafo, origem: str) -> List[str]:
        """
        Busca em profundidade manual (pilha implementada com lista).
        Retorna a ordem de visitação a partir de `origem`.
        """
        if not grafo.existe_vertice(origem):
            raise KeyError(f"Vértice de origem inexistente: {origem}")
        visitados = set()
        ordem = []
        pilha = [origem]
        while pilha:
            u = pilha.pop()
            if u in visitados:
                continue
            visitados.add(u)
            ordem.append(u)
            # empilha em ordem reversa para visitar os vizinhos na ordem "natural"
            for vizinho, _ in reversed(grafo.vizinhos(u)):
                if vizinho not in visitados:
                    pilha.append(vizinho)
        return ordem

    # ---------------- Conectividade ---------------- #
    @staticmethod
    def eh_conexo(grafo: Grafo) -> bool:
        """Um grafo é conexo se todo vértice é alcançável a partir de
        qualquer outro. Como o grafo é não-direcionado, basta uma BFS/DFS
        a partir de um vértice qualquer."""
        if grafo.numero_vertices() == 0:
            return True
        primeiro = next(iter(grafo.vertices())).id
        alcancados = AlgoritmosGrafo.bfs(grafo, primeiro)
        return len(alcancados) == grafo.numero_vertices()

    # ---------------- Vértice mais distante ---------------- #
    @staticmethod
    def vertice_mais_distante(grafo: Grafo, origem: str, excluir: Optional[Iterable[str]] = None) -> str:
        """
        Encontra, a partir de `origem`, o vértice alcançável com a MAIOR
        distância mínima (usa Dijkstra). É usado para reposicionar a
        Equipe Rocket bem longe após uma derrota.
        """
        dist, _ = AlgoritmosGrafo.dijkstra(grafo, origem)
        excluir = set(excluir or [])
        candidatos = {v: d for v, d in dist.items()
                      if d != float("inf") and v != origem and v not in excluir}
        if not candidatos:
            return origem
        maior = max(candidatos.values())
        empatados = [v for v, d in candidatos.items() if d == maior]
        return empatados[0]
