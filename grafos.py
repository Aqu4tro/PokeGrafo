import heapq

class GrafoRegiao:
    def __init__(self):
        self.adjacencias = {}

    def adicionar_rota(self, origem, destino, tempo):
        if origem not in self.adjacencias:
            self.adjacencias[origem] = {}
        if destino not in self.adjacencias:
            self.adjacencias[destino] = {}
            
        self.adjacencias[origem][destino] = int(tempo)
        self.adjacencias[destino][origem] = int(tempo) # Movimento em qualquer direção[cite: 1]

    def carregar_mapa_txt(self, nome_arquivo):
        with open(nome_arquivo, 'r') as arquivo:
            for linha in arquivo:
                dados = linha.strip().split(',')
                if len(dados) == 3:
                    self.adicionar_rota(dados[0], dados[1], dados[2])

    def caminho_minimo_dijkstra(self, origem, destino):
        """
        Algoritmo clássico de Dijkstra para achar a rota mais rápida.
        Ideal para quando o treinador precisa correr para o PMC.
        """
        distancias = {vertice: float('infinity') for vertice in self.adjacencias}
        distancias[origem] = 0
        fila_prioridade = [(0, origem)]
        caminho_anterior = {}

        while fila_prioridade:
            distancia_atual, vertice_atual = heapq.heappop(fila_prioridade)

            if vertice_atual == destino:
                break # Chegamos ao destino

            if distancia_atual > distancias[vertice_atual]:
                continue

            for vizinho, peso in self.adjacencias[vertice_atual].items():
                distancia = distancia_atual + peso
                if distancia < distancias[vizinho]:
                    distancias[vizinho] = distancia
                    caminho_anterior[vizinho] = vertice_atual
                    heapq.heappush(fila_prioridade, (distancia, vizinho))

        return distancias[destino], caminho_anterior
