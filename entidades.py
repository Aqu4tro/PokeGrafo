import random

class Pokemon:
    def __init__(self, nome, tipo):
        self.nome = nome
        self.tipo = tipo
        self.xp = 0
        self.hp = 100 # Inicia com máximo de HP
        
        # AP e DP aleatórios[cite: 1]
        self.ap = random.randint(20, 50)
        self.dp = random.randint(10, 30)
        self.fase_evolucao = 1 # Máximo de 3 fases[cite: 1]

    def esta_consciente(self):
        return self.hp >= 20 #[cite: 1]

    def ganhar_xp(self, quantidade):
        self.xp += quantidade
        # Verifica se evolui ao atingir 1000 XP[cite: 1]
        if self.xp >= 1000 and self.fase_evolucao < 3:
            self.evoluir()

    def evoluir(self):
        self.fase_evolucao += 1
        self.xp -= 1000
        # Em sua nova forma, AP e DP crescem 30%[cite: 1]
        self.ap = int(self.ap * 1.30)
        self.dp = int(self.dp * 1.30)
        print(f"\n🌟 O QUE É ISSO?! {self.nome} evoluiu para a fase {self.fase_evolucao}!")

class Treinador:
    def __init__(self, nome, local_atual):
        self.nome = nome
        self.local_atual = local_atual
        self.xp = 0
        self.pokemons = [] # Máximo 6 ativos[cite: 1]
        self.ovos = []
        self.insignias = 0
        self.pokebolas = 7 # Inicia com 7[cite: 1]

    def capturar_pokemon(self, pokemon_selvagem):
        if len(self.pokemons) < 6:
            self.pokemons.append(pokemon_selvagem)
            print(f"{pokemon_selvagem.nome} foi capturado com sucesso!")
        else:
            print(f"{pokemon_selvagem.nome} foi capturado e enviado ao Professor Carvalho!") #[cite: 1]
