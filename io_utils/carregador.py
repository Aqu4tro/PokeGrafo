"""Leitor do arquivo de região.

Interpreta o mapa/espécies/ginásios/configurações do arquivo de texto e
cria um objeto `Regiao` pronto para a simulação. Veja `data/mapa_regiao.txt`
para um exemplo do formato aceito.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional

from models.grafo import AlgoritmosGrafo, Grafo
from models.especie import Especie, Pokedex
from models.pokemon import Pokemon
from models.treinador import Treinador, LiderGinasio, MembroEquipeRocket
from models.item import Ovo, Erva, PokebolaExtra
from models.regiao import Regiao


class ErroArquivoRegiao(Exception):
    pass


def _dividir_secoes(caminho: str) -> Dict[str, List[str]]:
    secoes: Dict[str, List[str]] = {}
    secao_atual = None
    with open(caminho, "r", encoding="utf-8") as f:
        for linha_bruta in f:
            linha = linha_bruta.strip()
            if not linha or linha.startswith("#"):
                continue
            if linha.startswith("[") and linha.endswith("]"):
                secao_atual = linha[1:-1].strip().upper()
                secoes[secao_atual] = []
                continue
            if secao_atual is None:
                raise ErroArquivoRegiao(f"Linha fora de qualquer seção: {linha!r}")
            secoes[secao_atual].append(linha)
    return secoes


def _parse_chave_valor(linhas: List[str]) -> Dict[str, str]:
    resultado = {}
    for linha in linhas:
        if "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        resultado[chave.strip().lower()] = valor.strip()
    return resultado


def carregar_regiao(caminho_arquivo: str, seed_extra: Optional[int] = None) -> Regiao:
    secoes = _dividir_secoes(caminho_arquivo)

    for secao_obrigatoria in ("VERTICES", "ARESTAS", "ESPECIES"):
        if not secoes.get(secao_obrigatoria):
            raise ErroArquivoRegiao(
                f"A seção [{secao_obrigatoria}] é obrigatória e não pode estar vazia.")

    cfg_regiao = _parse_chave_valor(secoes.get("REGIAO", []))
    cfg_geral = _parse_chave_valor(secoes.get("CONFIG", []))

    seed = cfg_geral.get("seed")
    try:
        seed_numerica = int(seed) if seed else None
    except ValueError as erro:
        raise ErroArquivoRegiao(f"Seed inválida: {seed!r}.") from erro
    rng = random.Random(seed_numerica)
    if seed_extra is not None:
        rng = random.Random((seed_numerica or 0) + seed_extra)

    # ------------------------------------------------------------ #
    # 1) Grafo (vértices + arestas) -- Requisito Adicional 1 e 2
    # ------------------------------------------------------------ #
    grafo = Grafo()
    vertice_laboratorio = None
    ids_vertices = set()
    for linha in secoes.get("VERTICES", []):
        partes = [p.strip() for p in linha.split(";")]
        if len(partes) < 3:
            raise ErroArquivoRegiao(f"Vértice mal formatado: {linha!r}")
        id_v, nome_v, tipo_v = partes[0], partes[1], partes[2]
        if not id_v or id_v in ids_vertices:
            raise ErroArquivoRegiao(f"ID de vértice vazio ou duplicado: {id_v!r}")
        try:
            x = float(partes[3]) if len(partes) > 3 and partes[3] else 0.0
            y = float(partes[4]) if len(partes) > 4 and partes[4] else 0.0
            grafo.adicionar_vertice(id_v, nome_v, tipo_v, x, y)
        except ValueError as erro:
            raise ErroArquivoRegiao(f"Vértice inválido: {linha!r}: {erro}") from erro
        ids_vertices.add(id_v)
        if tipo_v == "laboratorio":
            vertice_laboratorio = id_v

    if vertice_laboratorio is None:
        raise ErroArquivoRegiao("Nenhum vértice do tipo 'laboratorio' foi definido no mapa.")

    for linha in secoes.get("ARESTAS", []):
        partes = [p.strip() for p in linha.split(";")]
        if len(partes) < 3:
            raise ErroArquivoRegiao(f"Aresta mal formatada: {linha!r}")
        origem, destino = partes[0], partes[1]
        if origem not in ids_vertices or destino not in ids_vertices:
            raise ErroArquivoRegiao(
                f"Aresta referencia vértice inexistente: {origem!r} -> {destino!r}.")
        try:
            peso = float(partes[2])
            grafo.adicionar_aresta(origem, destino, peso)
        except ValueError as erro:
            raise ErroArquivoRegiao(f"Aresta inválida: {linha!r}: {erro}") from erro

    if not AlgoritmosGrafo.eh_conexo(grafo):
        raise ErroArquivoRegiao("O mapa da região precisa formar um grafo conexo.")

    # ------------------------------------------------------------ #
    # 2) Espécies / Pokédex -- Requisito Adicional 5
    # ------------------------------------------------------------ #
    pokedex = Pokedex()
    ids_especies = set()
    for linha in secoes.get("ESPECIES", []):
        partes = [p.strip() for p in linha.split(";")]
        if len(partes) < 4:
            raise ErroArquivoRegiao(f"Espécie mal formatada: {linha!r}")
        id_e, nome_e = partes[0], partes[1]
        tipos = [t.strip() for t in partes[2].split(",") if t.strip()]
        if not id_e or id_e in ids_especies:
            raise ErroArquivoRegiao(f"ID de espécie vazio ou duplicado: {id_e!r}")
        if not tipos:
            raise ErroArquivoRegiao(f"A espécie {id_e!r} precisa possuir ao menos um tipo.")
        try:
            fase = int(partes[3])
        except ValueError as erro:
            raise ErroArquivoRegiao(f"Fase inválida em {linha!r}.") from erro
        if fase not in (1, 2, 3):
            raise ErroArquivoRegiao(f"A espécie {id_e!r} deve estar nas fases 1, 2 ou 3.")
        xp_evo = None
        if len(partes) > 4 and partes[4]:
            try:
                xp_evo = float(partes[4])
            except ValueError as erro:
                raise ErroArquivoRegiao(f"XP de evolução inválido em {linha!r}.") from erro
        evolui_para = partes[5] if len(partes) > 5 and partes[5] else None
        pokedex.registrar(Especie(id_e, nome_e, tipos, fase, xp_evo, evolui_para))
        ids_especies.add(id_e)

    for especie in pokedex.todas():
        if especie.evolui_para is None:
            continue
        if not pokedex.existe(especie.evolui_para):
            raise ErroArquivoRegiao(
                f"A evolução de {especie.id!r} referencia espécie inexistente: "
                f"{especie.evolui_para!r}.")
        proxima = pokedex.obter(especie.evolui_para)
        if proxima.fase != especie.fase + 1:
            raise ErroArquivoRegiao(
                f"A evolução {especie.id!r} -> {proxima.id!r} deve avançar exatamente uma fase.")

    ids_iniciais = [l.strip() for l in secoes.get("INICIAIS", []) if l.strip()]
    invalidos = [i for i in ids_iniciais if not pokedex.existe(i)]
    if invalidos:
        raise ErroArquivoRegiao(
            f"[INICIAIS] referencia espécies inexistentes: {', '.join(invalidos)}.")
    especies_iniciais = [pokedex.obter(i) for i in ids_iniciais]
    if not especies_iniciais:
        especies_iniciais = pokedex.especies_fase_inicial()
    if any(especie.fase != 1 for especie in especies_iniciais):
        raise ErroArquivoRegiao("Todos os Pokémon iniciais devem estar na fase 1.")

    # ------------------------------------------------------------ #
    # 3) Prazo máximo de inscrição -- Requisito Adicional 6
    #    (deve estar entre 10x e 15x a soma de todos os pesos das arestas)
    # ------------------------------------------------------------ #
    soma_pesos = grafo.soma_pesos_arestas()
    prazo_cfg = cfg_regiao.get("prazo_inscricao", "auto").lower()
    if prazo_cfg == "auto":
        prazo = soma_pesos * 12.0  # ponto médio confortável do intervalo [10x, 15x]
    else:
        try:
            prazo = float(prazo_cfg)
        except ValueError as erro:
            raise ErroArquivoRegiao(
                f"prazo_inscricao deve ser numérico ou 'auto': {prazo_cfg!r}.") from erro
        limite_inf, limite_sup = soma_pesos * 10.0, soma_pesos * 15.0
        if not (limite_inf <= prazo <= limite_sup):
            raise ErroArquivoRegiao(
                f"prazo_inscricao={prazo} fora do intervalo permitido "
                f"[{limite_inf:.1f}, {limite_sup:.1f}] (10x a 15x a soma dos pesos)."
            )

    regiao = Regiao(
        nome=cfg_regiao.get("nome", "Região Pokémon"),
        grafo=grafo,
        pokedex=pokedex,
        vertice_laboratorio=vertice_laboratorio,
        prazo_maximo_inscricao=prazo,
        especies_iniciais=especies_iniciais,
    )

    # ------------------------------------------------------------ #
    # 4) Líderes de ginásio
    # ------------------------------------------------------------ #
    vertices_normais = [v.id for v in grafo.vertices() if v.tipo == "normal"]

    for linha in secoes.get("GINASIOS", []):
        partes = [p.strip() for p in linha.split(";")]
        if len(partes) < 3:
            raise ErroArquivoRegiao(f"Ginásio mal formatado: {linha!r}")
        vertice_g, nome_lider, id_insignia = partes[0], partes[1], partes[2]
        if (not grafo.existe_vertice(vertice_g)
                or grafo.obter_vertice(vertice_g).tipo != "ginasio"):
            raise ErroArquivoRegiao(
                f"Ginásio referencia vértice inexistente ou de tipo incorreto: {vertice_g!r}.")
        fixo = True
        tempo_perm = 30.0
        tipo_time = None
        if len(partes) > 3 and partes[3]:
            fixo = partes[3].strip().lower() in ("true", "1", "sim", "verdadeiro")
        if len(partes) > 4 and partes[4]:
            try:
                tempo_perm = float(partes[4])
            except ValueError as erro:
                raise ErroArquivoRegiao(
                    f"Tempo de permanência inválido no ginásio: {linha!r}.") from erro
            if tempo_perm <= 0:
                raise ErroArquivoRegiao(
                    f"O tempo de permanência do líder deve ser positivo: {linha!r}.")
        if len(partes) > 5 and partes[5]:
            tipo_time = partes[5].strip().lower()

        lider = LiderGinasio(nome_lider, vertice_g, id_insignia, fixo, tempo_perm)
        candidatas = [e for e in pokedex.todas() if e.fase == 1 and tipo_time in e.tipos] \
            if tipo_time else (especies_iniciais or pokedex.todas())
        if not candidatas:
            candidatas = especies_iniciais or pokedex.todas()
        _equipar_time_aleatorio(lider, candidatas, pokedex, rng, tamanho=3)
        regiao.adicionar_treinador(lider)

    # ------------------------------------------------------------ #
    # 5) Treinadores NPC, pokémons selvagens, itens extras -- Requisito 4
    #    (posições e atributos sorteados aleatoriamente)
    # ------------------------------------------------------------ #
    def vertice_sorteado():
        return rng.choice(vertices_normais) if vertices_normais else grafo.vertice_aleatorio(rng)

    def quantidade_configurada(chave: str, padrao: int) -> int:
        valor_texto = cfg_geral.get(chave, str(padrao))
        try:
            valor = int(valor_texto)
        except ValueError as erro:
            raise ErroArquivoRegiao(
                f"A configuração {chave!r} deve ser um inteiro: {valor_texto!r}.") from erro
        if valor < 0:
            raise ErroArquivoRegiao(
                f"A configuração {chave!r} não pode ser negativa.")
        return valor

    num_treinadores = quantidade_configurada("num_treinadores_npc", 2)
    nomes_disponiveis = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fabio",
                          "Gabi", "Hugo", "Ines", "Joao", "Karen", "Lucas"]
    rng.shuffle(nomes_disponiveis)
    for i in range(num_treinadores):
        nome = nomes_disponiveis[i % len(nomes_disponiveis)]
        t = Treinador(f"Treinador {nome}", vertice_sorteado())
        t.xp = float(rng.randint(0, 50))
        _equipar_time_aleatorio(t, especies_iniciais or pokedex.todas(), pokedex, rng, tamanho=rng.randint(1, 3))
        regiao.adicionar_treinador(t)

    num_rocket = quantidade_configurada("num_membros_rocket", 0)
    for i in range(num_rocket):
        t = MembroEquipeRocket(f"Agente Rocket {i+1}", vertice_sorteado())
        _equipar_time_aleatorio(t, pokedex.todas(), pokedex, rng, tamanho=2)
        regiao.adicionar_treinador(t)

    num_selvagens = quantidade_configurada("num_pokemons_selvagens", 8)
    todas_especies_fase1 = pokedex.especies_fase_inicial() or pokedex.todas()
    for _ in range(num_selvagens):
        especie = rng.choice(todas_especies_fase1)
        p = _criar_pokemon_aleatorio(especie, pokedex, rng)
        regiao.adicionar_pokemon_selvagem(p, vertice_sorteado())

    num_itens_extras = quantidade_configurada("num_itens_extras", 3)
    for _ in range(num_itens_extras):
        regiao.adicionar_item(PokebolaExtra(vertice_sorteado()))

    num_ervas = quantidade_configurada("num_ervas", 3)
    for _ in range(num_ervas):
        regiao.adicionar_item(Erva(vertice_sorteado()))

    num_ovos = quantidade_configurada("num_ovos", 2)
    for _ in range(num_ovos):
        especie_oculta = rng.choice(todas_especies_fase1)
        regiao.adicionar_item(Ovo(vertice_sorteado(), especie_oculta, rng))

    return regiao


def _criar_pokemon_aleatorio(especie: Especie, pokedex: Pokedex, rng: random.Random) -> Pokemon:
    xp = float(rng.randint(0, 50))
    hp = rng.randint(60, 100)
    return Pokemon(especie, pokedex, hp=hp, xp=xp, rng=rng)


def _equipar_time_aleatorio(treinador: Treinador, especies_candidatas: List[Especie],
                             pokedex: Pokedex, rng: random.Random, tamanho: int = 3):
    especies_fase1 = [e for e in especies_candidatas if e.fase == 1] or especies_candidatas
    for _ in range(min(tamanho, Treinador.MAX_POKEMONS_ATIVOS)):
        especie = rng.choice(especies_fase1)
        pokemon = _criar_pokemon_aleatorio(especie, pokedex, rng)
        treinador.adicionar_pokemon(pokemon)
