# Importando as classes dos outros arquivos
from entidades import Pokemon, Treinador
from grafo import GrafoRegiao
# Aqui você também importaria a classe JogoInterativo que mostrei na resposta anterior

def main():
    # 1. Cria e carrega o mapa
    mapa_jogo = GrafoRegiao()
    # mapa_jogo.carregar_mapa_txt("mapa.txt") 
    # (Descomente acima e crie o txt. Por enquanto, adiciono manual para teste)
    mapa_jogo.adicionar_rota("Laboratório", "Rota 1", 50)
    mapa_jogo.adicionar_rota("Rota 1", "Ginásio", 60)
    mapa_jogo.adicionar_rota("Ginásio", "Centro Médico", 30)

    # 2. Configura o Jogador
    jogador = Treinador("Ash", "Laboratório")
    inicial = Pokemon("Charmander", "Fogo")
    jogador.pokemons.append(inicial)

    # 3. Inicia o Jogo
    # jogo = JogoInterativo(jogador, mapa_jogo)
    # jogo.iniciar()
    
    print("Jogo configurado com sucesso! Arquitetura modularizada pronta.")

if __name__ == "__main__":
    main()
