# PokeGrafo - Rumo à Liga Pokémon

Projeto da disciplina de Algoritmos em Grafos da Universidade Federal do
Cariri (UFCA), desenvolvido em Python com orientação a objetos e interface
gráfica Tkinter.

## Funcionalidades

- Grafo ponderado, não direcionado e carregado de arquivo texto.
- Lista de adjacência, heap mínimo, Dijkstra, BFS e DFS implementados sem
  bibliotecas prontas de grafos.
- Mapa com laboratório, ginásios, Centros Médicos Pokémon (PMC), estádio e
  vértices comuns.
- Três Pokémon iniciais simultâneos, um de água, um de fogo e um de grama. Se
  o jogador recusar, recebe somente um Pokémon aleatório de fase inicial.
- Inventário inicial com incubadora e exatamente sete Pokébolas.
- Equipe com até seis Pokémon ativos e limite total de sete considerando ovos
  e Pokémon que aguardam a escolha de excedente.
- Escolha manual do Pokémon enviado ao Professor Carvalho quando a equipe está
  cheia.
- Capturas com validação de local e estoque, consumo de uma Pokébola por
  tentativa e opção de abandono em qualquer turno. Os danos anteriores à fuga
  são preservados e o selvagem permanece escondido daquele treinador.
- Ovos de espécie oculta que eclodem após exatamente 100 unidades percorridas.
- HP, XP, AP, DP, recuperação, ervas, inconsciência, ferimento grave e
  evolução. Cada evolução aumenta AP e DP em 30%.
- Tratamento médico cujo temporizador só avança enquanto o treinador permanece
  parado em um PMC.
- Relógio do mundo sincronizado com o custo da viagem do jogador. NPCs, líderes
  móveis, Equipe Rocket e Pokémon selvagens entram em estado de trânsito e só
  chegam ao próximo vértice após consumir exatamente o peso da aresta.
- Batalhas 3x3 com validações no motor: mesmo vértice, três Pokémon conscientes
  e bloqueio em PMC e laboratório.
- Aceitação ou recusa do desafio, desistência do treinador desafiado, escolha
  manual de ataque e substituição do Pokémon do jogador.
- Dano calculado estritamente por `max(0, AP efetivo - DP efetivo)`, sem poder
  adicional nem dano mínimo artificial. Bloqueios mútuos terminam por
  desistência técnica do desafiado, sem alterar HP.
- Batalhas sem empate e XP concedido aos Pokémon que efetivamente venceram ou
  perderam cada duelo.
- Tabela de tipos disponível para consulta e Equipe Rocket como elemento extra.
- Inscrição na Liga condicionada às insígnias e ao prazo configurado; ao
  ultrapassar o prazo, o treinador é marcado imediatamente como inapto.
- Interface com fuga de captura por turno, desistência do desafiado e indicação
  visual dos estados `Em trânsito` e `Inapto`.

## Requisitos

- Python 3.9 ou superior.
- Tkinter para a interface gráfica.
- Pytest 8 para a suíte automatizada.

No Ubuntu ou Debian, caso Tkinter não esteja instalado:

```bash
sudo apt install python3-tk
```

## Instalação e execução

```bash
git clone https://github.com/Aqu4tro/PokeGrafo
cd PokeGrafo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Para carregar outro mapa:

```bash
python3 main.py data/outro_mapa.txt
```

### Docker

```bash
docker build -t pokegrafo .
docker run --rm -it -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix pokegrafo
```

## Testes

A suíte segue o padrão de descoberta do pytest e usa RNG controlado para que
os resultados sejam determinísticos.

Execute todos os testes com:

```bash
pytest -q
```

Para saída detalhada:

```bash
pytest -v
```

Para transformar qualquer aviso em falha:

```bash
pytest -q -W error
```

Os testes cobrem:

- Dijkstra, BFS, DFS, conectividade, heap e tabela de tipos.
- Três iniciais e recusa dos iniciais.
- Estoque e consumo de Pokébolas, captura, abandono e caminhos negativos.
- Limites de equipe, escolha de excedente e ovos.
- Eclosão exatamente em 100 unidades e evolução com aumento de 30%.
- Recuperação natural, ervas, inconsciência, ferimento grave, tratamento no PMC
  e pausa do tratamento durante movimento.
- Separação entre tempo e distância, incluindo a ausência de XP por distância
  durante 100 turnos parado no PMC.
- Sincronização do relógio e duração ponderada do movimento de NPCs, líderes,
  Rocket e selvagens.
- Pré-condições de batalha, recusa, desistência, ataques, substituição, ausência
  de empate, fórmula exata de dano, bônus de AP/DP e XP individual por duelo.
- Abandono no meio de uma captura com preservação dos HPs.
- Roubo, derrota, invisibilidade e reaparecimento distante da Equipe Rocket.
- Patrulha completa dos líderes móveis, incluindo permanência e retorno ao
  ginásio.
- Contenção de mapas inválidos e cálculo das fronteiras inclusivas do prazo de
  inscrição na Liga.

## Regras importantes do motor

As regras de domínio são validadas em `engine/simulacao.py` e nos módulos de
`models/`. A GUI apenas coleta decisões. Portanto, chamadas programáticas não
podem ignorar co-localização, zonas seguras, pertencimento da equipe, estoque
de Pokébolas ou tamanho dos times.

Ataques são representados por `models/ataque.py` e Pokémon de fases superiores
recebem opções adicionais. O repertório identifica a escolha do treinador, mas
não acrescenta poder à fórmula obrigatória. Quando os dois Pokémon são
matematicamente incapazes de causar dano, o motor encerra o bloqueio por uma
desistência técnica do desafiado; nenhum HP é removido artificialmente.

O método de passagem de tempo recebe separadamente tempo e distância. Assim,
recuperação natural e repouso podem avançar enquanto o treinador está parado,
mas XP de crescimento e incubação de ovos só avançam com distância efetivamente
percorrida.

## Formato de `data/mapa_regiao.txt`

- `[REGIAO]`: nome e prazo de inscrição. `auto` usa 12 vezes a soma dos pesos,
  dentro do intervalo obrigatório de 10 a 15 vezes.
- `[VERTICES]`: `id;nome;tipo;x;y`. Tipos: `normal`, `ginasio`, `pmc`,
  `estadio` e `laboratorio`.
- `[ARESTAS]`: `origem;destino;peso`, sempre positivo.
- `[ESPECIES]`: `id;nome;tipos;fase;xp_para_evoluir;evolui_para`.
- `[INICIAIS]`: espécies de fase inicial oferecidas pelo professor. A
  configuração precisa fornecer opções distintas de água, fogo e grama.
- `[GINASIOS]`:
  `vertice_id;nome_lider;id_insignia;fixo;tempo_permanencia;tipo_time`.
- `[CONFIG]`: quantidades de treinadores, selvagens, itens, ervas, ovos e
  membros da Equipe Rocket, além da seed de geração. Quantidades negativas,
  referências inexistentes, grafo desconexo e prazo fora da faixa são
  rejeitados pelo carregador.

## Estrutura

```text
PokeGrafo/
├── main.py
├── engine/
│   └── simulacao.py
├── gui/
│   └── app.py
├── io_utils/
│   └── carregador.py
├── models/
│   ├── ataque.py
│   ├── batalha.py
│   ├── especie.py
│   ├── grafo.py
│   ├── item.py
│   ├── pokemon.py
│   ├── regiao.py
│   └── treinador.py
├── data/
│   └── mapa_regiao.txt
└── tests/
    ├── conftest.py
    ├── test_batalha.py
    ├── test_dominio.py
    ├── test_grafo.py
    └── test_regressao_auditoria.py
```

## Autores e vídeos

- Wesley Geilson - estrutura de vértices, grafos, Dijkstra e heap mínimo:
  https://youtu.be/qnzvW3Q6SAU?is=8vk1kwHNQzoxtCA2
- Irlan Barros - DFS e vértice mais distante: 
https://www.youtube.com/watch?v=PvxYY1gFYwc.
- Jonatas Levi - BFS, conectividade e elementos extras:
  https://www.youtube.com/watch?v=B9ArQKqr-G4

O link de Irlan deve substituir o aviso acima assim que a URL for fornecida.

## Observação

O mundo é reconstruído do arquivo texto a cada execução; ainda não há sistema
de salvamento persistente. A seed da configuração torna a geração inicial
reproduzível.
