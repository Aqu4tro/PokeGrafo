# Sistemas de inventario que os atores vão ter
class Inventario:
    def __init__(self):
        self.pokemons: List[Pokemon] = []
        self._pokebolas_livres: int = 0
        self._incubadoras: int = 0
        self._ervas_medicinais: int = 0
        self._ovos: List[Pokemon] = []