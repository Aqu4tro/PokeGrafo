"""
gui/app.py
==========
Interface gráfica (Tkinter, biblioteca padrão do Python) do projeto Rumo à
Liga Pokémon.

Layout:
    * Barra superior: nome da região, prazo de inscrição, relógio do jogador.
    * Esquerda: canvas com o mapa (vértices coloridos por tipo, arestas com
      peso, marcador do jogador). Clicar em um vértice vizinho move o
      jogador; clicar em um vértice distante oferece caminhar até lá pelo
      caminho mínimo (Dijkstra).
    * Direita: abas com a equipe do jogador, o que há no local atual (para
      desafiar treinadores, capturar pokémons selvagens e coletar itens) e
      ações gerais (avançar o mundo, tratar no PMC, inscrever-se na Liga).
    * Rodapé: registro (log) de eventos da simulação.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List, Optional

from models.grafo import AlgoritmosGrafo
from models.pokemon import Pokemon, StatusPokemon
from models.treinador import Treinador, LiderGinasio, MembroEquipeRocket
from models.item import Item, Ovo, Erva, PokebolaExtra
from engine.simulacao import Simulacao
from io_utils.carregador import carregar_regiao

CORES_TIPO_VERTICE = {
    "normal": "#B0BEC5",
    "ginasio": "#FFA726",
    "pmc": "#66BB6A",
    "estadio": "#FFD54F",
    "laboratorio": "#42A5F5",
}

CORES_STATUS_POKEMON = {
    StatusPokemon.CONSCIENTE: "#43A047",
    StatusPokemon.INCONSCIENTE: "#FB8C00",
    StatusPokemon.MUITO_MACHUCADO: "#E53935",
    StatusPokemon.NO_PMC: "#1E88E5",
}

RAIO_VERTICE = 24


class AplicativoPokemonLiga:
    def __init__(self, root: tk.Tk, caminho_mapa: str):
        self.root = root
        self.root.title("Rumo à Liga Pokémon")
        self.root.geometry("1260x780")
        self.root.minsize(1000, 650)

        self.regiao = carregar_regiao(caminho_mapa)
        self.sim = Simulacao(self.regiao)
        self.jogador: Optional[Treinador] = None

        self._ids_vertice_no_canvas = {}  # vertice_id -> item_id do círculo (para clique)

        self._construir_interface()
        self.root.after(150, self._fluxo_inicial)

    # ================================================================== #
    # Construção da interface
    # ================================================================== #
    def _construir_interface(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        # ---- barra superior ---- #
        barra_topo = ttk.Frame(self.root, padding=8)
        barra_topo.pack(side="top", fill="x")

        self.lbl_regiao = ttk.Label(barra_topo, text=self.regiao.nome, font=("Segoe UI", 14, "bold"))
        self.lbl_regiao.pack(side="left")

        self.lbl_status_topo = ttk.Label(barra_topo, text="", font=("Segoe UI", 10))
        self.lbl_status_topo.pack(side="right")

        # ---- área principal: mapa (esquerda) + abas (direita) ---- #
        painel_principal = ttk.Panedwindow(self.root, orient="horizontal")
        painel_principal.pack(side="top", fill="both", expand=True, padx=6, pady=4)

        frame_mapa = ttk.Frame(painel_principal)
        painel_principal.add(frame_mapa, weight=3)

        self.canvas = tk.Canvas(frame_mapa, bg="#ECEFF1", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        legenda = ttk.Frame(frame_mapa, padding=(4, 4))
        legenda.pack(side="bottom", fill="x")
        for tipo, cor in CORES_TIPO_VERTICE.items():
            item = tk.Canvas(legenda, width=14, height=14, highlightthickness=0)
            item.create_oval(1, 1, 13, 13, fill=cor, outline="#333")
            item.pack(side="left", padx=(6, 2))
            ttk.Label(legenda, text=tipo.capitalize()).pack(side="left", padx=(0, 8))

        frame_direita = ttk.Frame(painel_principal, width=380)
        painel_principal.add(frame_direita, weight=2)

        self.notebook = ttk.Notebook(frame_direita)
        self.notebook.pack(fill="both", expand=True)

        self.aba_equipe = ttk.Frame(self.notebook, padding=6)
        self.aba_local = ttk.Frame(self.notebook, padding=6)
        self.aba_mover = ttk.Frame(self.notebook, padding=6)
        self.aba_geral = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.aba_equipe, text="Equipe")
        self.notebook.add(self.aba_local, text="Neste local")
        self.notebook.add(self.aba_mover, text="Mover")
        self.notebook.add(self.aba_geral, text="Ações gerais")

        self._construir_aba_geral()

        # ---- rodapé: log ---- #
        frame_log = ttk.LabelFrame(self.root, text="Registro de eventos", padding=4)
        frame_log.pack(side="bottom", fill="x")
        self.texto_log = tk.Text(frame_log, height=8, state="disabled", wrap="word",
                                  bg="#111", fg="#EEE", font=("Consolas", 9))
        self.texto_log.pack(side="left", fill="both", expand=True)
        rolagem = ttk.Scrollbar(frame_log, command=self.texto_log.yview)
        rolagem.pack(side="right", fill="y")
        self.texto_log.configure(yscrollcommand=rolagem.set)

        self.canvas.bind("<Configure>", lambda e: self._desenhar_mapa())

    def _construir_aba_geral(self):
        f = self.aba_geral
        ttk.Label(f, text="Ações gerais", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        ttk.Button(f, text="⏱  Avançar o mundo (1 passo)",
                   command=self._acao_avancar_mundo).pack(fill="x", pady=3)
        ttk.Button(f, text="🏥  Tratar equipe no PMC",
                   command=self._acao_tratar_pmc).pack(fill="x", pady=3)
        ttk.Button(f, text="🏆  Inscrever-se na Liga (no estádio)",
                   command=self._acao_registrar_liga).pack(fill="x", pady=3)

        ttk.Separator(f).pack(fill="x", pady=10)
        ttk.Label(f, text="Depósito do Prof. Carvalho", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.lbl_deposito = ttk.Label(f, text="", wraplength=320, justify="left")
        self.lbl_deposito.pack(anchor="w", pady=(2, 10))

        ttk.Label(f, text="Ovos carregados", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.lbl_ovos = ttk.Label(f, text="", wraplength=320, justify="left")
        self.lbl_ovos.pack(anchor="w", pady=(2, 10))

        ttk.Label(f, text="Prazo de inscrição", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.barra_prazo = ttk.Progressbar(f, maximum=100, value=0)
        self.barra_prazo.pack(fill="x", pady=(2, 2))
        self.lbl_prazo = ttk.Label(f, text="")
        self.lbl_prazo.pack(anchor="w")

    # ================================================================== #
    # Fluxo inicial: nome do jogador + pokémon inicial
    # ================================================================== #
    def _fluxo_inicial(self):
        nome = simpledialog.askstring("Bem-vindo(a) treinador(a)!",
                                       "Qual é o seu nome de treinador(a)?",
                                       parent=self.root) or "Ash"

        especies = self.sim.especies_iniciais_disponiveis()
        escolha = DialogoEscolhaInicial(self.root, especies).mostrar()
        self.jogador = self.sim.criar_jogador(nome, escolha)

        self._atualizar_tudo()

    # ================================================================== #
    # Desenho do mapa
    # ================================================================== #
    def _desenhar_mapa(self):
        self.canvas.delete("all")
        self._ids_vertice_no_canvas.clear()
        grafo = self.regiao.grafo

        vertices = list(grafo.vertices())
        if not vertices:
            return
        max_x = max(v.x for v in vertices) or 1
        max_y = max(v.y for v in vertices) or 1
        largura = max(self.canvas.winfo_width(), 400)
        altura = max(self.canvas.winfo_height(), 400)
        margem = 60
        escala_x = (largura - 2 * margem) / max_x if max_x else 1
        escala_y = (altura - 2 * margem) / max_y if max_y else 1

        def posicao(v):
            return margem + v.x * escala_x, margem + v.y * escala_y

        # arestas (desenhadas antes dos vértices, para ficarem "atrás")
        desenhadas = set()
        for v in vertices:
            x1, y1 = posicao(v)
            for viz_id, peso in grafo.vizinhos(v.id):
                chave = tuple(sorted((v.id, viz_id)))
                if chave in desenhadas:
                    continue
                desenhadas.add(chave)
                viz = grafo.obter_vertice(viz_id)
                x2, y2 = posicao(viz)
                self.canvas.create_line(x1, y1, x2, y2, fill="#90A4AE", width=2)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.create_rectangle(mx - 12, my - 9, mx + 12, my + 9,
                                              fill="#ECEFF1", outline="")
                self.canvas.create_text(mx, my, text=f"{peso:g}", font=("Segoe UI", 8), fill="#455A64")

        # vértices
        for v in vertices:
            x, y = posicao(v)
            cor = CORES_TIPO_VERTICE.get(v.tipo, "#CCC")
            eh_local_jogador = self.jogador is not None and self.jogador.vertice_atual == v.id
            contorno = "#D32F2F" if eh_local_jogador else "#37474F"
            espessura = 4 if eh_local_jogador else 2
            item_id = self.canvas.create_oval(x - RAIO_VERTICE, y - RAIO_VERTICE,
                                               x + RAIO_VERTICE, y + RAIO_VERTICE,
                                               fill=cor, outline=contorno, width=espessura)
            self.canvas.tag_bind(item_id, "<Button-1>", lambda e, vid=v.id: self._ao_clicar_vertice(vid))
            self.canvas.create_text(x, y + RAIO_VERTICE + 12, text=v.nome, font=("Segoe UI", 8, "bold"))
            self._ids_vertice_no_canvas[v.id] = item_id

            # indicadores de conteúdo do vértice
            n_selvagens = len(self.regiao.pokemons_selvagens_em(v.id))
            n_itens = len(self.regiao.itens_em(v.id))
            n_treinadores = len([t for t in self.regiao.treinadores_em(v.id)
                                  if not (self.jogador and t.id == self.jogador.id)])
            if n_selvagens:
                self._indicador(x + 16, y - 16, "#2E7D32", str(n_selvagens))
            if n_itens:
                self._indicador(x - 16, y - 16, "#F9A825", str(n_itens))
            if n_treinadores:
                self._indicador(x + 16, y + 16, "#1565C0", str(n_treinadores))

    def _indicador(self, x, y, cor, texto):
        self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill=cor, outline="white")
        self.canvas.create_text(x, y, text=texto, font=("Segoe UI", 7, "bold"), fill="white")

    # ================================================================== #
    # Clique no mapa / movimentação
    # ================================================================== #
    def _ao_clicar_vertice(self, vertice_id: str):
        if self.jogador is None:
            return
        if vertice_id == self.jogador.vertice_atual:
            return
        vizinhos = dict(self.regiao.grafo.vizinhos(self.jogador.vertice_atual))
        if vertice_id in vizinhos:
            self._mover_um_passo(vertice_id)
        else:
            caminho, distancia = self.sim.calcular_rota(self.jogador.vertice_atual, vertice_id)
            if not caminho:
                messagebox.showinfo("Sem rota", "Não há caminho até esse local.")
                return
            nome_destino = self.regiao.grafo.obter_vertice(vertice_id).nome
            if messagebox.askyesno(
                    "Caminhar até lá?",
                    f"Ir até {nome_destino} custará {distancia:g} unidades de tempo, "
                    f"passando por {len(caminho) - 1} vértice(s). Deseja seguir esse caminho "
                    f"(calculado com o algoritmo de Dijkstra)?"):
                for passo in caminho[1:]:
                    self._mover_um_passo(passo, atualizar=False)
                self._atualizar_tudo()

    def _mover_um_passo(self, destino: str, atualizar: bool = True):
        try:
            msgs = self.sim.mover_um_passo(self.jogador, destino)
            self._log(msgs)
        except ValueError as e:
            messagebox.showerror("Movimento inválido", str(e))
        if atualizar:
            self._atualizar_tudo()

    # ================================================================== #
    # Ações
    # ================================================================== #
    def _acao_avancar_mundo(self):
        msgs = self.sim.avancar_mundo(1)
        self._log(msgs or ["O mundo avançou um passo (nada de novo aconteceu)."])
        self._atualizar_tudo()

    def _acao_tratar_pmc(self):
        try:
            msgs = self.sim.tratar_no_pmc(self.jogador)
            self._log(msgs)
        except ValueError as e:
            messagebox.showwarning("Aviso", str(e))
        self._atualizar_tudo()

    def _acao_registrar_liga(self):
        try:
            msg = self.sim.registrar_na_liga(self.jogador)
            messagebox.showinfo("Inscrição na Liga", msg)
        except ValueError as e:
            messagebox.showwarning("Aviso", str(e))
        self._atualizar_tudo()

    def _acao_desafiar(self, oponente: Treinador):
        if not self.regiao.batalha_permitida_em(self.jogador.vertice_atual):
            messagebox.showwarning("Proibido", "Batalhas não são permitidas neste local.")
            return
        if not self.jogador.pode_batalhar_treinador():
            messagebox.showwarning("Equipe insuficiente",
                                    "Você precisa de ao menos 3 pokémons conscientes para desafiar "
                                    "outro treinador.")
            return
        if not oponente.pode_batalhar_treinador():
            messagebox.showinfo("Indisponível", f"{oponente.nome} não tem pokémons suficientes "
                                                 f"conscientes para batalhar agora.")
            return

        disponiveis = self.jogador.pokemons_disponiveis()
        escolha = DialogoSelecaoPokemon(self.root, "Escolha até 3 pokémons para a batalha",
                                         disponiveis, minimo=1, maximo=3).mostrar()
        if not escolha:
            return
        escolha_oponente = oponente.pokemons_disponiveis()[:3]
        resultado = self.sim.desafiar_treinador(self.jogador, oponente, escolha, escolha_oponente)
        self._log(resultado.log)
        vencedor = getattr(resultado, "vencedor_treinador", None)
        if vencedor is self.jogador:
            messagebox.showinfo("Vitória!", f"Você venceu {oponente.nome}!")
        elif vencedor is oponente:
            messagebox.showinfo("Derrota", f"Você perdeu para {oponente.nome}.")
        self._atualizar_tudo()

    def _acao_capturar(self, selvagem: Pokemon):
        if not self.regiao.batalha_permitida_em(self.jogador.vertice_atual):
            messagebox.showwarning("Proibido", "Capturas não são permitidas neste local.")
            return
        disponiveis = self.jogador.pokemons_disponiveis()
        if not disponiveis:
            messagebox.showwarning("Equipe indisponível", "Nenhum dos seus pokémons está consciente.")
            return
        escolha = DialogoSelecaoPokemon(self.root, f"Escolha o pokémon para desafiar {selvagem.apelido}",
                                         disponiveis, minimo=1, maximo=1).mostrar()
        if not escolha:
            return
        resultado = self.sim.capturar(self.jogador, escolha[0], selvagem)
        self._log(resultado.log)
        if resultado.capturado:
            messagebox.showinfo("Capturado!", f"{selvagem.apelido} agora faz parte da sua equipe!")
        self._atualizar_tudo()

    def _acao_coletar(self, item: Item):
        msg = self.sim.coletar_item(self.jogador, item)
        self._log([msg])
        self._atualizar_tudo()

    # ================================================================== #
    # Atualização dos painéis
    # ================================================================== #
    def _atualizar_tudo(self):
        self._atualizar_barra_topo()
        self._atualizar_aba_equipe()
        self._atualizar_aba_local()
        self._atualizar_aba_mover()
        self._atualizar_aba_geral()
        self._desenhar_mapa()

    def _atualizar_barra_topo(self):
        if self.jogador is None:
            return
        total_ginasios = self.regiao.total_ginasios()
        necessarias = self.jogador.numero_insignias_necessarias(total_ginasios)
        texto = (f"Treinador: {self.jogador.nome}   |   XP: {self.jogador.xp:.0f}   |   "
                 f"Insígnias: {len(self.jogador.insignias)}/{necessarias}   |   "
                 f"Local: {self.regiao.grafo.obter_vertice(self.jogador.vertice_atual).nome}")
        self.lbl_status_topo.configure(text=texto)

    def _atualizar_aba_equipe(self):
        for w in self.aba_equipe.winfo_children():
            w.destroy()
        if self.jogador is None:
            return
        if not self.jogador.equipe:
            ttk.Label(self.aba_equipe, text="Sua equipe está vazia.").pack(anchor="w")
            return
        for p in self.jogador.equipe:
            self._construir_cartao_pokemon(self.aba_equipe, p)

    def _construir_cartao_pokemon(self, pai, p: Pokemon):
        moldura = ttk.LabelFrame(pai, text=f"{p.apelido}  (fase {p.fase})", padding=6)
        moldura.pack(fill="x", pady=4)
        ttk.Label(moldura, text=f"Espécie: {p.especie.nome}  |  Tipo(s): {'/'.join(p.tipos)}"
                  ).pack(anchor="w")
        barra = ttk.Progressbar(moldura, maximum=100, value=p.hp)
        barra.pack(fill="x", pady=(4, 0))
        cor_status = CORES_STATUS_POKEMON.get(p.status, "#000")
        linha = ttk.Frame(moldura)
        linha.pack(fill="x", pady=(2, 0))
        ttk.Label(linha, text=f"HP {p.hp}/100").pack(side="left")
        canvas_dot = tk.Canvas(linha, width=10, height=10, highlightthickness=0)
        canvas_dot.create_oval(1, 1, 9, 9, fill=cor_status, outline="")
        canvas_dot.pack(side="left", padx=(8, 4))
        ttk.Label(linha, text=p.status.replace("_", " ").capitalize()).pack(side="left")
        ttk.Label(moldura, text=f"XP {p.xp:.0f}  |  AP {p.ap:.1f}  |  DP {p.dp:.1f}").pack(anchor="w")

    def _atualizar_aba_local(self):
        for w in self.aba_local.winfo_children():
            w.destroy()
        if self.jogador is None:
            return
        vertice = self.regiao.grafo.obter_vertice(self.jogador.vertice_atual)
        ttk.Label(self.aba_local, text=f"{vertice.nome} ({vertice.tipo})",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        if not self.regiao.batalha_permitida_em(vertice.id):
            ttk.Label(self.aba_local, text="⚠ Batalhas e capturas são proibidas aqui.",
                      foreground="#B71C1C").pack(anchor="w", pady=(0, 8))

        outros_treinadores = self.regiao.treinadores_em(vertice.id, excluir_id=self.jogador.id)
        selvagens = self.regiao.pokemons_selvagens_em(vertice.id)
        itens = self.regiao.itens_em(vertice.id)

        if outros_treinadores:
            ttk.Label(self.aba_local, text="Treinadores presentes:", font=("Segoe UI", 10, "bold")
                      ).pack(anchor="w")
            for t in outros_treinadores:
                linha = ttk.Frame(self.aba_local)
                linha.pack(fill="x", pady=2)
                rotulo = t.nome
                if isinstance(t, LiderGinasio):
                    rotulo += "  (Líder de Ginásio)"
                ttk.Label(linha, text=rotulo).pack(side="left")
                ttk.Button(linha, text="Desafiar", command=lambda t=t: self._acao_desafiar(t)
                           ).pack(side="right")

        if selvagens:
            ttk.Label(self.aba_local, text="Pokémons selvagens:", font=("Segoe UI", 10, "bold")
                      ).pack(anchor="w", pady=(8, 0))
            for p in selvagens:
                linha = ttk.Frame(self.aba_local)
                linha.pack(fill="x", pady=2)
                ttk.Label(linha, text=f"{p.apelido} (HP {p.hp}, XP {p.xp:.0f})").pack(side="left")
                ttk.Button(linha, text="Capturar", command=lambda p=p: self._acao_capturar(p)
                           ).pack(side="right")

        if itens:
            ttk.Label(self.aba_local, text="Itens:", font=("Segoe UI", 10, "bold")
                      ).pack(anchor="w", pady=(8, 0))
            for it in itens:
                linha = ttk.Frame(self.aba_local)
                linha.pack(fill="x", pady=2)
                ttk.Label(linha, text=self._nome_item(it)).pack(side="left")
                ttk.Button(linha, text="Coletar", command=lambda it=it: self._acao_coletar(it)
                           ).pack(side="right")

        if not outros_treinadores and not selvagens and not itens:
            ttk.Label(self.aba_local, text="Nada de especial por aqui.").pack(anchor="w")

    @staticmethod
    def _nome_item(item: Item) -> str:
        if isinstance(item, Ovo):
            return "Ovo misterioso 🥚"
        if isinstance(item, Erva):
            return "Erva medicinal 🌿 (+10 HP à equipe consciente)"
        if isinstance(item, PokebolaExtra):
            return "Pokébola extra 🔴"
        return "Item"

    def _atualizar_aba_mover(self):
        for w in self.aba_mover.winfo_children():
            w.destroy()
        if self.jogador is None:
            return
        ttk.Label(self.aba_mover, text="Vértices vizinhos (1 passo):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        vizinhos = self.regiao.grafo.vizinhos(self.jogador.vertice_atual)
        if not vizinhos:
            ttk.Label(self.aba_mover, text="(nenhum)").pack(anchor="w")
        for vid, peso in vizinhos:
            nome = self.regiao.grafo.obter_vertice(vid).nome
            linha = ttk.Frame(self.aba_mover)
            linha.pack(fill="x", pady=2)
            ttk.Label(linha, text=f"{nome}  (custo {peso:g})").pack(side="left")
            ttk.Button(linha, text="Ir", command=lambda vid=vid: self._mover_um_passo(vid)
                       ).pack(side="right")

        ttk.Separator(self.aba_mover).pack(fill="x", pady=10)
        ttk.Label(self.aba_mover, text="Ir até um local específico (caminho mínimo):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ids_ordenados = sorted(self.regiao.grafo.ids_vertices(),
                                key=lambda i: self.regiao.grafo.obter_vertice(i).nome)
        nomes = [self.regiao.grafo.obter_vertice(i).nome for i in ids_ordenados]
        self._mapa_nome_para_id = dict(zip(nomes, ids_ordenados))
        self.combo_destino = ttk.Combobox(self.aba_mover, values=nomes, state="readonly")
        self.combo_destino.pack(fill="x", pady=4)
        ttk.Button(self.aba_mover, text="Calcular caminho e ir",
                   command=self._ir_ate_selecionado).pack(fill="x")

    def _ir_ate_selecionado(self):
        nome = self.combo_destino.get()
        if not nome:
            return
        destino = self._mapa_nome_para_id.get(nome)
        if destino:
            self._ao_clicar_vertice(destino)

    def _atualizar_aba_geral(self):
        if self.jogador is None:
            return
        deposito = self.jogador.deposito_professor
        self.lbl_deposito.configure(
            text=", ".join(p.apelido for p in deposito) if deposito else "(vazio)")
        ovos = self.jogador.ovos
        if ovos:
            texto_ovos = ", ".join(f"Ovo #{o.id} ({o.progresso_percentual():.0f}% incubado)"
                                    for o in ovos)
        else:
            texto_ovos = "(nenhum)"
        self.lbl_ovos.configure(text=texto_ovos)

        prazo = self.regiao.prazo_maximo_inscricao
        usado = self.jogador.distancia_percorrida
        pct = min(100, 100 * usado / prazo) if prazo else 0
        self.barra_prazo.configure(value=pct)
        self.lbl_prazo.configure(text=f"{usado:.0f} / {prazo:.0f} unidades utilizadas")

    # ================================================================== #
    def _log(self, mensagens: List[str]):
        if not mensagens:
            return
        self.texto_log.configure(state="normal")
        for m in mensagens:
            self.texto_log.insert("end", f"• {m}\n")
        self.texto_log.see("end")
        self.texto_log.configure(state="disabled")


# ========================================================================== #
# Diálogos auxiliares
# ========================================================================== #
class DialogoEscolhaInicial:
    def __init__(self, master, especies):
        self.top = tk.Toplevel(master)
        self.top.title("Escolha seu pokémon inicial")
        self.top.grab_set()
        self.top.resizable(False, False)
        self.resultado = None

        ttk.Label(self.top, text="O Prof. Carvalho oferece três pokémons iniciais:",
                  font=("Segoe UI", 11, "bold")).pack(padx=16, pady=(16, 8))

        self.var = tk.StringVar(value="")
        for e in especies:
            ttk.Radiobutton(self.top, text=f"{e.nome}  (tipo: {'/'.join(e.tipos)})",
                             variable=self.var, value=e.id).pack(anchor="w", padx=24, pady=2)
        ttk.Radiobutton(self.top, text="Nenhum -- prefiro um pokémon aleatório do laboratório",
                         variable=self.var, value="").pack(anchor="w", padx=24, pady=(8, 12))

        ttk.Button(self.top, text="Confirmar", command=self._confirmar).pack(pady=(0, 16))
        self.top.protocol("WM_DELETE_WINDOW", self._confirmar)

    def _confirmar(self):
        self.resultado = self.var.get() or None
        self.top.destroy()

    def mostrar(self):
        self.top.wait_window()
        return self.resultado


class DialogoSelecaoPokemon:
    def __init__(self, master, titulo: str, pokemons: List[Pokemon], minimo=1, maximo=3):
        self.top = tk.Toplevel(master)
        self.top.title(titulo)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.resultado: Optional[List[Pokemon]] = None
        self.minimo, self.maximo = minimo, maximo

        ttk.Label(self.top, text=titulo, font=("Segoe UI", 10, "bold"),
                  wraplength=340).pack(padx=16, pady=(16, 8))

        self.vars = []
        for p in pokemons:
            v = tk.BooleanVar(value=False)
            self.vars.append((v, p))
            ttk.Checkbutton(self.top, text=f"{p.apelido}  (HP {p.hp}, XP {p.xp:.0f}, "
                                            f"AP {p.ap:.1f}, DP {p.dp:.1f})",
                             variable=v).pack(anchor="w", padx=24, pady=2)

        ttk.Button(self.top, text="Confirmar", command=self._confirmar).pack(pady=12)
        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)

    def _confirmar(self):
        escolhidos = [p for v, p in self.vars if v.get()]
        if not (self.minimo <= len(escolhidos) <= self.maximo):
            messagebox.showwarning("Seleção inválida",
                                    f"Escolha entre {self.minimo} e {self.maximo} pokémon(s).",
                                    parent=self.top)
            return
        self.resultado = escolhidos
        self.top.destroy()

    def mostrar(self):
        self.top.wait_window()
        return self.resultado


def executar_aplicativo(caminho_mapa: str = "data/mapa_regiao.txt"):
    root = tk.Tk()
    AplicativoPokemonLiga(root, caminho_mapa)
    root.mainloop()
