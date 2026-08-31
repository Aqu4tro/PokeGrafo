"""Representa um pokémon: estado (HP, XP, status) e comportamento.

AP e DP são calculados a partir de valores iniciais, mais 10% do XP e
eventuais bônus de batalha; evolução e regras relacionadas seguem o
enunciado do projeto.
"""

from __future__ import annotations
import random
from typing import Optional, List

from models.especie import Especie, Pokedex
from models.ataque import ataques_para


class StatusPokemon:
    CONSCIENTE = "consciente"
    INCONSCIENTE = "inconsciente"          # nocauteado em batalha, aguardando tempo de recuperação
    MUITO_MACHUCADO = "muito_machucado"    # HP < 5, precisa ser levado ao PMC
    NO_PMC = "em_tratamento_pmc"           # sendo tratado no Centro Médico Pokémon


class Pokemon:
    _proximo_id = 1

    def __init__(self, especie: Especie, pokedex: Pokedex,
                 ap_inicial: Optional[float] = None, dp_inicial: Optional[float] = None,
                 hp: int = 100, xp: float = 0.0, apelido: Optional[str] = None,
                 rng: Optional[random.Random] = None):
        rng = rng or random
        self.id = Pokemon._proximo_id
        Pokemon._proximo_id += 1

        self.especie = especie
        self._pokedex = pokedex
        self.apelido = apelido or especie.nome

        # Valores iniciais de AP/DP: aleatórios, conforme o enunciado, caso
        # não sejam explicitamente fornecidos (ex.: ovos herdam da espécie).
        self.ap_inicial = ap_inicial if ap_inicial is not None else rng.uniform(10, 30)
        self.dp_inicial = dp_inicial if dp_inicial is not None else rng.uniform(10, 30)

        self.xp = xp
        self.hp = max(1, min(100, hp))
        self.bonus_batalha_ap = 0.0
        self.bonus_batalha_dp = 0.0

        self.status = StatusPokemon.CONSCIENTE
        self._timer_inconsciente = 0.0   # unidades de distância restantes
        self._timer_pmc = 0.0            # unidades de distância restantes no PMC
        self._acumulo_regen = 0.0        # unidades acumuladas para regen natural de HP
        self._acumulo_distancia_xp = 0.0  # unidades acumuladas para XP por distância

        self.vertice_atual: Optional[str] = None
        self.treinador_id: Optional[int] = None  # None = pokémon selvagem
        self.transito_origem: Optional[str] = None
        self.transito_destino: Optional[str] = None
        self.transito_tempo_total: float = 0.0
        self.transito_tempo_restante: float = 0.0
        self._recalcular_status(rng)

    # ------------------------------------------------------------------ #
    # Propriedades derivadas
    # ------------------------------------------------------------------ #
    @property
    def ap(self) -> float:
        return self.ap_inicial + 0.10 * self.xp + self.bonus_batalha_ap

    @property
    def dp(self) -> float:
        return self.dp_inicial + 0.10 * self.xp + self.bonus_batalha_dp

    @property
    def nome(self) -> str:
        return self.especie.nome

    @property
    def tipos(self) -> List[str]:
        return self.especie.tipos

    @property
    def fase(self) -> int:
        return self.especie.fase

    @property
    def ataques(self):
        """Ataques conhecidos na fase atual, sempre escolhidos explicitamente."""
        return ataques_para(self.tipos, self.fase)

    def esta_disponivel(self) -> bool:
        """Pode ser escolhido para uma batalha?"""
        return self.status == StatusPokemon.CONSCIENTE

    def esta_selvagem(self) -> bool:
        return self.treinador_id is None

    @property
    def em_transito(self) -> bool:
        return self.transito_destino is not None

    @property
    def progresso_transito(self) -> float:
        if not self.em_transito or self.transito_tempo_total <= 0:
            return 0.0
        consumido = self.transito_tempo_total - self.transito_tempo_restante
        return max(0.0, min(1.0, consumido / self.transito_tempo_total))

    def iniciar_transito(self, destino: str, peso_aresta: float):
        """Inicia uma aresta sem alterar o vértice ocupado pelo Pokémon."""
        if self.em_transito:
            raise ValueError(f"{self.apelido} já está em trânsito.")
        if peso_aresta <= 0:
            raise ValueError("O tempo de uma aresta deve ser positivo.")
        self.transito_origem = self.vertice_atual
        self.transito_destino = destino
        self.transito_tempo_total = float(peso_aresta)
        self.transito_tempo_restante = float(peso_aresta)

    def avancar_transito(self, unidades: float,
                         rng: Optional[random.Random] = None) -> bool:
        """Consome tempo da aresta e retorna ``True`` apenas na chegada."""
        if not self.em_transito or unidades <= 0:
            return False
        consumido = min(float(unidades), self.transito_tempo_restante)
        self.transito_tempo_restante -= consumido
        self.tick(consumido, rng, distancia_percorrida=consumido)
        if self.transito_tempo_restante > 0:
            return False
        self.vertice_atual = self.transito_destino
        self.cancelar_transito()
        return True

    def cancelar_transito(self):
        self.transito_origem = None
        self.transito_destino = None
        self.transito_tempo_total = 0.0
        self.transito_tempo_restante = 0.0

    # ------------------------------------------------------------------ #
    # Dano / status
    # ------------------------------------------------------------------ #
    def receber_dano(self, dano: float, rng: Optional[random.Random] = None):
        rng = rng or random
        if dano <= 0:
            return
        self.hp = max(1, min(100, self.hp - int(round(dano))))
        self._recalcular_status(rng)

    def _recalcular_status(self, rng: random.Random):
        if self.hp < 5:
            self.status = StatusPokemon.MUITO_MACHUCADO
            self._timer_inconsciente = 0.0
        elif self.hp < 20:
            if self.status not in (StatusPokemon.INCONSCIENTE,):
                # acabou de ser nocauteado agora: sorteia o tempo de recuperação
                self._timer_inconsciente = rng.uniform(10, 50)
            self.status = StatusPokemon.INCONSCIENTE
        else:
            self.status = StatusPokemon.CONSCIENTE
            self._timer_inconsciente = 0.0

    # ------------------------------------------------------------------ #
    # PMC (Centro Médico Pokémon)
    # ------------------------------------------------------------------ #
    def iniciar_tratamento_pmc(self, rng: Optional[random.Random] = None):
        rng = rng or random
        self._timer_pmc = rng.uniform(10, 50)
        self.status = StatusPokemon.NO_PMC

    # ------------------------------------------------------------------ #
    # Erva medicinal
    # ------------------------------------------------------------------ #
    def usar_erva(self):
        """+10 HP se o pokémon estiver consciente; não afeta inconscientes
        (eles 'não conseguem tomar o remédio', conforme o enunciado)."""
        if self.status == StatusPokemon.CONSCIENTE:
            self.hp = min(100, self.hp + 10)

    # ------------------------------------------------------------------ #
    # Passagem de tempo (chamado a cada passo de simulação / movimento)
    # ------------------------------------------------------------------ #
    def tick(self, unidades_tempo: float, rng: Optional[random.Random] = None,
             em_tratamento_estacionario: bool = False,
             distancia_percorrida: float = 0.0):
        """Avança saúde pelo tempo e XP somente pela distância efetiva.

        Tempo parado continua resolvendo inconsciência e regeneração natural,
        mas nunca alimenta o acumulador de XP por distância.
        """
        rng = rng or random
        if unidades_tempo <= 0:
            return

        if self.status == StatusPokemon.MUITO_MACHUCADO:
            # HP permanece congelado até ser tratado no PMC (regra explícita do enunciado)
            return

        if self.status == StatusPokemon.NO_PMC:
            # O tratamento só progride enquanto o treinador permanece parado
            # no PMC. Caminhar pausa o relógio médico.
            if not em_tratamento_estacionario:
                return
            self._timer_pmc -= unidades_tempo
            if self._timer_pmc <= 0:
                self.hp = 100
                self.status = StatusPokemon.CONSCIENTE
                self._timer_pmc = 0.0
            return

        if self.status == StatusPokemon.INCONSCIENTE:
            self._timer_inconsciente -= unidades_tempo
            self._regenerar_hp(unidades_tempo)
            if self._timer_inconsciente <= 0:
                # ao fim do período de recuperação, o pokémon acorda consciente
                self.hp = max(self.hp, 20)
                self.status = StatusPokemon.CONSCIENTE
                self._timer_inconsciente = 0.0
            return

        # CONSCIENTE: regeneração natural de HP + ganho de XP por distância
        self._regenerar_hp(unidades_tempo)
        self.ganhar_xp_por_distancia(distancia_percorrida, rng)

    def _regenerar_hp(self, unidades: float):
        if self.hp >= 100:
            return
        self._acumulo_regen += unidades
        ganho = int(self._acumulo_regen // 10)
        if ganho > 0:
            self._acumulo_regen -= ganho * 10
            self.hp = min(100, self.hp + ganho)

    # ------------------------------------------------------------------ #
    # Experiência (XP) e evolução
    # ------------------------------------------------------------------ #
    def ganhar_xp_por_distancia(self, unidades: float, rng: Optional[random.Random] = None):
        """+1 XP a cada 100 unidades de distância percorridas."""
        self._acumulo_distancia_xp += unidades
        ganho = int(self._acumulo_distancia_xp // 100)
        if ganho > 0:
            self._acumulo_distancia_xp -= ganho * 100
            self.ganhar_xp(ganho, rng)

    def ganhar_xp(self, quantidade: float, rng: Optional[random.Random] = None):
        rng = rng or random
        if quantidade <= 0:
            return
        self.xp += quantidade
        self._verificar_evolucao(rng)

    def registrar_vitoria_batalha(self, xp_oponente: float, rng: Optional[random.Random] = None):
        """Chamado quando ESTE pokémon vence uma batalha."""
        rng = rng or random
        if xp_oponente >= self.xp:
            self.bonus_batalha_ap += 1
            self.bonus_batalha_dp += 1
        self.ganhar_xp(10, rng)

    def registrar_derrota_batalha(self, rng: Optional[random.Random] = None):
        """Chamado quando ESTE pokémon perde uma batalha."""
        self.ganhar_xp(3, rng)

    def registrar_captura(self, rng: Optional[random.Random] = None):
        """+3 XP ao pokémon do treinador que participou de uma captura bem-sucedida."""
        self.ganhar_xp(3, rng)

    def _verificar_evolucao(self, rng: random.Random):
        especie = self.especie
        if especie.xp_para_evoluir is None or especie.evolui_para is None:
            return
        if self.xp < especie.xp_para_evoluir:
            return
        proxima = self._pokedex.proxima_evolucao(especie)
        if proxima is None:
            return
        self._evoluir_para(proxima)
        # evolução em cadeia: se o XP já for suficiente para a fase seguinte também
        self._verificar_evolucao(rng)

    def _evoluir_para(self, nova_especie: Especie):
        ap_total_antes = self.ap
        dp_total_antes = self.dp

        self.especie = nova_especie

        novo_ap_total = ap_total_antes * 1.30
        novo_dp_total = dp_total_antes * 1.30

        # recalibra a base para que a fórmula (ap_inicial + 10%xp + bonus)
        # já reflita o novo total imediatamente, e continue crescendo
        # corretamente a partir de agora.
        self.ap_inicial = novo_ap_total - 0.10 * self.xp - self.bonus_batalha_ap
        self.dp_inicial = novo_dp_total - 0.10 * self.xp - self.bonus_batalha_dp

    # ------------------------------------------------------------------ #
    def resumo(self) -> str:
        return (f"{self.apelido} ({self.especie.nome}, fase {self.fase}, "
                f"tipos={'/'.join(self.tipos)}) | HP {self.hp}/100 | "
                f"XP {self.xp:.0f} | AP {self.ap:.1f} | DP {self.dp:.1f} | "
                f"status={self.status}")

    def __repr__(self):
        return f"Pokemon(#{self.id} {self.apelido}, {self.especie.id})"
