#!/usr/bin/env python3
"""
main.py
=======
Ponto de entrada do projeto "Rumo à Liga Pokémon".

Uso:
    python3 main.py                       # usa data/mapa_regiao.txt
    python3 main.py caminho/outro_mapa.txt # usa outro arquivo de região
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import executar_aplicativo

if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "mapa_regiao.txt")
    executar_aplicativo(caminho)
