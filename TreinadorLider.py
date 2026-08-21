# Classe Filha que é um Lider de ginasio

class TreinadorLiderPokemon(TreinadorPokemon):
    def __init__(self):
        super().__init__()
        self.insignia: bool = True