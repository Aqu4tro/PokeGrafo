# Classe pai que tem as caracteristicas gerais de treinadores de pokemons

class TreinadorPokemon(ABC):
    def __init__(self):
        self._xp: float = 0.0
        self._inventario: Inventario = Inventario()
    
    @property
    def xp(self) -> float:
        return self._xp
    
    @property
    def inventario(self) -> Inventario:
        return self._inventario