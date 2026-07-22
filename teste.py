import sys

class JogoInterativo:
    def __init__(self, jogador, mapa):
        self.jogador = jogador
        self.mapa = mapa
        self.tempo_gasto = 0
        self.prazo_maximo_inscricao = 5000 # O prazo deve ser entre 10x e 15x a soma dos pesos das arestas.pdf]
        self.jogando = True

    def iniciar(self):
        print("\n" + "="*40)
        print("🎮 BEM-VINDO À LIGA POKÉMON! 🎮")
        print("="*40)
        
        while self.jogando:
            self.exibir_status_resumido()
            self.exibir_menu()
            escolha = input("\n👉 Escolha uma ação (1-5): ").strip()
            self.processar_acao(escolha)
            
            # Condição de derrota por tempo
            if self.tempo_gasto > self.prazo_maximo_inscricao:
                print("\n⏰ O PRAZO ACABOU! Você foi considerado inapto para o torneio.")
                self.jogando = False

    def exibir_status_resumido(self):
        print("\n" + "-"*40)
        print(f"📍 Local Atual: {self.jogador.local_atual}")
        print(f"🏅 Insígnias: {self.jogador.insignias}/8")
        print(f"⏳ Tempo: {self.tempo_gasto} / {self.prazo_maximo_inscricao}")
        print("-"*40)

    def exibir_menu(self):
        print("1. 🚶 Viajar para outra cidade")
        print("2. ⚔️  Procurar Batalha (Selvagem ou Treinador)")
        print("3. 🌿 Preparar Poção com Ervas Especiais")
        print("4. 📋 Ver Status da Equipe Pokémon")
        print("5. 🚪 Sair do Jogo")

    def processar_acao(self, escolha):
        if escolha == '1':
            self.menu_viajar()
        elif escolha == '2':
            self.menu_batalha()
        elif escolha == '3':
            self.usar_ervas_especiais()
        elif escolha == '4':
            self.ver_equipe()
        elif escolha == '5':
            print("\nSalvando seu progresso (na imaginação)... Até a próxima!")
            self.jogando = False
        else:
            print("\n❌ Opção inválida! Digite um número de 1 a 5.")

    def menu_viajar(self):
        # Lista as conexões disponíveis a partir do vértice atual
        destinos = self.mapa.adjacencias.get(self.jogador.local_atual, {})
        
        if not destinos:
            print("\nVocê está preso e não há rotas de saída!")
            return

        print("\n🛣️ Rotas disponíveis:")
        rotas = list(destinos.keys())
        for i, destino in enumerate(rotas):
            distancia = destinos[destino]
            print(f"[{i}] {destino} (Distância: {distancia})")
            
        print(f"[{len(rotas)}] Cancelar")
        
        try:
            opcao = int(input("Para onde deseja ir? "))
            if 0 <= opcao < len(rotas):
                destino_escolhido = rotas[opcao]
                distancia = destinos[destino_escolhido]
                
                print(f"\nViagem iniciada para {destino_escolhido}...")
                self.jogador.local_atual = destino_escolhido
                self.tempo_gasto += distancia
                
                # Aqui você chama a função que recupera HP, choca ovo e dá XP passivo
                print(f"Você caminhou por {distancia} unidades de distância.")
            else:
                print("Viagem cancelada.")
        except ValueError:
            print("Entrada inválida!")

    def menu_batalha(self):
        print("\nVocê encontrou um Pokémon Selvagem!")
        print("1. Lutar e tentar capturar")
        print("2. Fugir")
        
        escolha = input("O que vai fazer? ")
        if escolha == '1':
            print("Iniciando batalha...")
            # Aqui você conectaria com a lógica de batalha em turnos
        elif escolha == '2':
            # O treinador pode desistir de capturar o pokémon selvagem e abandonar a luta, deixando-o fugir.pdf]
            print("Você fugiu em segurança. O Pokémon selvagem se escondeu.")
        else:
            print("Ação inválida.")

    def usar_ervas_especiais(self):
        # O treinador pode preparar uma porção e aumentar os HP's em 10 unidades.pdf]
        print("\n🌿 Você preparou uma poção com ervas especiais!")
        for pokemon in self.jogador.pokemons:
            if pokemon.esta_consciente():
                pokemon.hp = min(100, pokemon.hp + 10) # Não ultrapassando o máximo de 100.pdf]
                print(f"{pokemon.nome} recuperou 10 HP! (HP Atual: {pokemon.hp})")
            else:
                # Pokémons inconscientes permanecem inconscientes, pois não conseguem tomar o remédio.pdf]
                print(f"{pokemon.nome} está inconsciente e não pode tomar o remédio.")

    def ver_equipe(self):
        print("\n📋 Sua Equipe:")
        if not self.jogador.pokemons:
            print("Você ainda não tem Pokémons!")
            return
            
        for i, p in enumerate(self.jogador.pokemons):
            status = "Consciente" if p.esta_consciente() else "Inconsciente"
            print(f"[{i+1}] {p.nome} (Tipo: {p.tipo}) - HP: {p.hp}/100 | XP: {p.xp} | AP: {p.ap} | DP: {p.dp} | Status: {status}")
