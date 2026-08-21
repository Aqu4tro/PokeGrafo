# Classe Pokemon com seus devidos atributos
# (Definida antes para o Inventário poder reconhecê-la)

class Pokemon:
    def __init__(self, nome: str, tipo: TipoPokemon, hp: float, xp: float, ap: float, dp: float):
        self._nome = nome
        self._tipo = tipo
        self._hp = hp
        self._xp = xp
        self._ap = ap
        self._dp = dp

    # Exemplo de Getter em Python (substitui o getNome)
    @property
    def nome(self) -> str:
        return self._nome

    # Exemplo de Setter em Python (substitui o setNome)
    @nome.setter
    def nome(self, valor: str):
        self._nome = valor