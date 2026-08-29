# PokeGrafo, rumo à liga Pokémon!

# Rumo à Liga Pokémon

### Esse projeto é uma parte avaliativa da cadeira de algoritmos em grafos ministrada por Carlos Vinícius, professor da UFCA. Abaixo estão as informações do projeto e sua arquitetura:
---
## Tecnologias Usadas

- **Python**
- **Paradigma Usado:** POO
- **IDEs:** Visual Studio Code / Pycharm
---
## Requisitos Obrigatorios
| Característica | Descrição |
| :--- | :--- |
| **Objetivo Principal** | Obter 3 insígnias diferentes dos lideres de ginasio. |
| **Dinâmica de Movimentação** | Os lideres se movimenta, mas retorna ao seu lugar de origem periodicamente. treinadores comuns e Pokémon selvagens apenas movem-se livremente. |
| **Limite da Equipe pokemon** | Os treinadores podem têm 6 Pokémon, incluindo o jogador. |
| **Escolha Inicial** | Inicialmente, o jogador escolhe 3 Pokémon distintos (ou 1 aleatório). |
| **Sistema de Experiência** | Lógica de XP. |
| **Sistema de Status** | Atributos: HP, AP, DP, vida, ataque e defesa respectivamente. |
| **Nivelamento de Pokémon** | Os Pokémon evoluem. |
| **Nivelamento de Treinador**| XP treinador. |
| **Sistema de Ovos** | Lógica de ovo. |
| **Batalhas e Saúde** | Lógica de luta e recuperação de hp por caminhar. |
| **Elementos / Tipagem** | Tipos de pokémon (fogo, água, planta…). |
| **Centro de Cura** | PMC, centro de recuperação dos pokémons. |
| **Sistema de Captura** | Sistema de captura de pokémons, só é possivel capturar se tiver pokebolas. |
| **Gerenciamento de Excedentes**| Sistema que escolhe qual pokemon vc fica caso pegue mais de 6 pokemon. (MECANICA NAO TESTADA)|
| **Condição de Game Over** | Condição de Derrota por tempo, caso ele não consiga as insígnias a tempo. |
| **Sistema de Inventário** | Sistema gerencie a posse de uma incubadora, um conjunto de 7 pokébolas e as porções de ervas medicinais encontradas. (Sistema de gerenciamento de ervas não implementado) |

## Requisitos Adicionais e Especificações do Grafo

| Característica | Descrição |
| :--- | :--- |
| **Entrada de Dados** | O programa deve ler a descrição de um grafo ponderado a partir de um arquivo texto. |
| **Estrutura do Mapa** | O grafo descreve as diferente possibilidades de caminhos a serem percorridos durante a jornada, contendo vértices, arestas e pesos nas arestas, representando o tempo necessário para percorrer tal aresta entre suas extremidades. Considere que é possível se mover em qualquer direção e passar pontos e arestas quantas vezes desejar. |
| **Pontos de Interesse** | Considere que o treinador pokémon possui um mapa completo da região, com as distâncias entre pontos adjacentes indicadas no mapa, além das posições dos ginásios, MCP e estádio para inscrição, além do ponto inicial do centro do Professor Carvalho. |
| **Geração de Entidades** | O arquivo também indica quantos pokémons, treinadores e itens extras existem na região. Além disso, as localizações, os pontos XP’s, HP’s, AP’s, DP’s de cada pokémon/treinador/item que já estão espalhados na região deve ser escolhida de forma aleatória. |
| **Evoluções** | Os níveis de evoluções entre pokémons deve ser especificado no arquivo. |
| **Cálculo do Prazo Máximo** | Também deve-se representar o prazo de tempo máximo para que se realize a inscrição no torneio (esse valor deve ser condizente com os valores dados de tempo de percurso entre cada ponto, devendo ser ao menos igual a 10 vezes a soma de todos os pesos nas arestas e no máximo igual a 15 vezes tal soma). |
| **Regras de Movimento e Zonas Seguras**| Os treinadores pokémons e pokémons da região podem se mover livremente estando em qualquer ponto. Batalhas no MCP e laboratório do Professor Carvalho são proibidas. Considere que cada pokémon e treinador move-se um vértice por vez durante a região. |

## Requisitos Opcionais (Elementos Extras)

| Característica | Descrição |
| :--- | :--- |
| **Vantagens de Tipo** | Quais tipos tem vantagens sobre quais outros e como são representados; Implementação das batalhas utilizando as diferenças entre os tipos. |
| **Equipe Rocket** | Implementação de uma Equipe Rocket, ou seja, uma equipe de treinadores que rouba pokémons e/ou insígnias de outros treinadores e possuem pokémons próprios. A cada derrota, a Equipe Rocket é enviada para um lugar aleatório e distante do ponto de ataque. Em caso de vitória, a mesma foge e fica invisível por um certo tempo, reaparecendo em algum lugar qualquer, posteriormente. O roubo exige vencer um duelo pokémon. |

## Autores

- **Jonatas Levi**
- **Irlan barros**
- **Wesley Geilson**

## Curso

- **Universidade:** Universidade Federal do Cariri (UFCA)
- **Professor:** Carlos Vinicius
- **Localidade:** Juazeiro do Norte – CE, 2026

## Como executar

```bash
cd pokemon_liga
python3 main.py                        
python3 main.py data/outro_mapa.txt     
```

Requer apenas Python 3.9+ com Tkinter (`sudo apt install python3-tk` no
Ubuntu/Debian, caso não venha instalado). Nenhuma dependência externa
(`pip install`) é necessária, tudo usa apenas a biblioteca padrão.

Para rodar o teste de integração (sem interface):

```bash
python3 -m tests.teste_simulacao
```

## Estrutura do projeto

```
pokemon_liga/
├── main.py                     
├── models/
│   ├── grafo.py                
│   ├── especie.py               
│   ├── pokemon.py             
│   ├── treinador.py             
│   ├── item.py                  
│   ├── batalha.py               
│   └── regiao.py               
├── io_utils/
│   └── carregador.py            
├── engine/
│   └── simulacao.py             
├── gui/
│   └── app.py                   
├── data/
│   └── mapa_regiao.txt          
└── tests/
    └── teste_simulacao.py       
```


## Formato do arquivo de região (`data/mapa_regiao.txt`)

- `[REGIAO]`: nome da região e prazo de inscrição (`auto` calcula
  automaticamente um valor entre 10x e 15x a soma dos pesos das arestas).
- `[VERTICES]`: `id;nome;tipo;x;y` — tipos válidos: `normal`, `ginasio`,
  `pmc`, `estadio`, `laboratorio`. `(x,y)` são coordenadas de desenho.
- `[ARESTAS]`: `origem;destino;peso` (grafo não-direcionado).
- `[ESPECIES]`: `id;nome;tipos;fase;xp_para_evoluir;evolui_para` — define
  as cadeias evolutivas (no máximo 3 fases, nomes distintos por fase).
- `[INICIAIS]`: ids de espécies (fase 1) oferecidas ao jogador.
- `[GINASIOS]`: `vertice_id;nome_lider;id_insignia;fixo;tempo_permanencia;tipo_time`.
- `[CONFIG]`: quantidades de treinadores NPC, pokémons selvagens, itens
  extras, ervas, ovos e membros da Equipe Rocket a serem espalhados
  **aleatoriamente** pelos vértices `normal`,
  
## Limitações

- A IA dos treinadores NPC comuns é propositalmente simples (caminham
  aleatoriamente) eles não iniciam batalhas entre si automaticamente
  o foco é a interação principal, para manter o escopo do
  projeto gerenciável.
- O sistema de "ataques" é simplificado para um único tipo de ataque
  básico (AP vs DP) por turno, entao, é gerado turnos excessivos em certos combates
- Não há persistência (salvar/carregar progresso do jogador), cada
  execução gera um novo estado a partir do arquivo de região (com `seed`
  fixa, o mundo gerado é sempre o mesmo e mas o progresso do jogador não é
  salvo ).


## Vídeos da equipe

- Wesley (Estrutura inicial de vertices e grafos e uso do Dijkstra e heap mínimo): https://youtu.be/qnzvW3Q6SAU?is=8vk1kwHNQzoxtCA2
- Irlan (DFS + vértice mais distante): 
- Jonatas (BFS + conectividade + Elementos Extras): 
