"""
models/batalha.py
==================
Sistema de batalhas: duelos individuais entre dois pokémons, batalhas
completas entre dois treinadores (3 pokémons de cada lado), captura de
pokémons selvagens e batalhas de ginásio.

Fórmulas adotadas (o enunciado descreve as regras qualitativamente, mas não
dá fórmulas exatas -- as escolhas abaixo são um design razoável e estão
documentadas também no README):

* Dano base = max(0, AP_efetivo_atacante - DP_efetivo_defensor).
  "AP/DP efetivo" inclui o bônus de XP do treinador quando a batalha é
  entre dois treinadores: "cada pokémon recebe AP's e DP's a mais que os
  XP's de seu treinador" (bônus não se aplica ao lado selvagem em capturas,
  pois pokémons selvagens não têm treinador).
* Multiplicador de tipo (item extra) é aplicado sobre o dano base.
* Probabilidade de esquiva/crítico = min(0.5, |gap de XP dos pokémons| / 100),
  conforme o enunciado ("proporcional à diferença em módulo dos XP's").
* Cada batalha (não importa o número de turnos) consome 1 unidade de
  tempo/distância percorrida do(s) treinador(es) envolvidos, conforme o
  enunciado ("cada batalha dura o equivalente a uma unidade de tempo
  percorrido").
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple

from models.pokemon import Pokemon, StatusPokemon
from models.treinador import Treinador
from models.especie import multiplicador_de_dano

PROB_MAXIMA_ESQUIVA_OU_CRITICO = 0.5
ESCALA_PROB_XP = 100.0


def _probabilidade_por_xp(gap_xp: float) -> float:
    return min(PROB_MAXIMA_ESQUIVA_OU_CRITICO, abs(gap_xp) / ESCALA_PROB_XP)


class ResultadoDuelo:
    def __init__(self):
        self.log: List[str] = []
        self.vencedor: Optional[Pokemon] = None
        self.perdedor: Optional[Pokemon] = None
        self.capturado: bool = False
        self.abandonado: bool = False


class SistemaBatalha:
    """Agrupa as operações de batalha. Não guarda estado -- recebe os
    objetos de treinador/pokémon envolvidos em cada chamada."""

    # ------------------------------------------------------------------ #
    # Duelo pokémon-a-pokémon (bloco básico usado por todas as batalhas)
    # ------------------------------------------------------------------ #
    @staticmethod
    def duelo(atacante: Pokemon, defensor: Pokemon,
              bonus_xp_atacante: float = 0.0, bonus_xp_defensor: float = 0.0,
              rng: Optional[random.Random] = None,
              log: Optional[List[str]] = None) -> Optional[Pokemon]:
        """
        Executa UM turno de ataque de `atacante` contra `defensor`.
        Retorna o pokémon que ficou inconsciente/muito machucado neste
        turno (ou None se ninguém caiu).
        """
        rng = rng or random
        log = log if log is not None else []

        ap_eff = atacante.ap + bonus_xp_atacante
        dp_eff = defensor.dp + bonus_xp_defensor
        dano_base = max(0.0, ap_eff - dp_eff)

        if dano_base <= 0:
            log.append(f"{atacante.apelido} ataca {defensor.apelido}, mas não causa dano "
                        f"(AP {ap_eff:.1f} <= DP {dp_eff:.1f}).")
            return None

        gap_xp = defensor.xp - atacante.xp
        prob_esquiva = _probabilidade_por_xp(gap_xp)
        if rng.random() < prob_esquiva:
            log.append(f"{defensor.apelido} esquiva do ataque de {atacante.apelido}! "
                        f"(chance {prob_esquiva*100:.0f}%)")
            return None

        multiplicador_tipo = multiplicador_de_dano(atacante.tipos, defensor.tipos)
        dano = dano_base * multiplicador_tipo

        prob_critico = _probabilidade_por_xp(atacante.xp - defensor.xp)
        critico = rng.random() < prob_critico
        if critico:
            dano *= 2
            log.append(f"Golpe crítico de {atacante.apelido}! (chance {prob_critico*100:.0f}%)")

        efetividade = ""
        if multiplicador_tipo > 1.0:
            efetividade = " -- é super efetivo!"
        elif multiplicador_tipo < 1.0:
            efetividade = " -- não é muito efetivo..."

        defensor.receber_dano(dano, rng)
        log.append(f"{atacante.apelido} ataca {defensor.apelido} causando {dano:.1f} de dano"
                    f"{efetividade} (HP restante: {defensor.hp}/100).")

        if not defensor.esta_disponivel():
            log.append(f"{defensor.apelido} ficou inconsciente!")
            return defensor
        return None

    # ------------------------------------------------------------------ #
    # Captura de pokémon selvagem
    # ------------------------------------------------------------------ #
    @staticmethod
    def tentar_captura(treinador: Treinador, pokemon_treinador: Pokemon,
                        pokemon_selvagem: Pokemon, rng: Optional[random.Random] = None,
                        max_turnos: int = 20) -> ResultadoDuelo:
        rng = rng or random
        resultado = ResultadoDuelo()
        resultado.log.append(f"{treinador.nome} desafia {pokemon_selvagem.apelido} selvagem "
                              f"usando {pokemon_treinador.apelido}!")

        bonus_treinador = treinador.xp  # só o lado do treinador tem bônus; selvagem não tem treinador
        for _ in range(max_turnos):
            if not pokemon_selvagem.esta_disponivel():
                break
            if not pokemon_treinador.esta_disponivel():
                break
            # No combate de captura, o pokémon selvagem ataca primeiro (ele foi "desafiado")
            caido = SistemaBatalha.duelo(pokemon_selvagem, pokemon_treinador,
                                          0.0, bonus_treinador, rng, resultado.log)
            if caido:
                break
            caido = SistemaBatalha.duelo(pokemon_treinador, pokemon_selvagem,
                                          bonus_treinador, 0.0, rng, resultado.log)
            if caido:
                break

        if not pokemon_selvagem.esta_disponivel():
            resultado.capturado = True
            resultado.vencedor = pokemon_treinador
            resultado.perdedor = pokemon_selvagem
            resultado.log.append(f"{pokemon_selvagem.apelido} foi capturado por {treinador.nome}!")
            pokemon_treinador.registrar_captura(rng)
            treinador.registrar_captura_bem_sucedida()
        elif not pokemon_treinador.esta_disponivel():
            resultado.vencedor = pokemon_selvagem
            resultado.perdedor = pokemon_treinador
            resultado.log.append(f"{pokemon_treinador.apelido} não resistiu. A captura falhou.")

        # cada batalha consome 1 unidade de tempo percorrido
        pokemon_treinador.tick(1.0, rng)
        pokemon_selvagem.tick(1.0, rng)
        treinador.distancia_percorrida += 1.0
        return resultado

    # ------------------------------------------------------------------ #
    # Batalha completa entre dois treinadores (3 pokémons de cada lado)
    # ------------------------------------------------------------------ #
    @staticmethod
    def batalha_treinadores(desafiante: Treinador, desafiado: Treinador,
                             time_desafiante: List[Pokemon], time_desafiado: List[Pokemon],
                             rng: Optional[random.Random] = None,
                             max_turnos: int = 60) -> ResultadoDuelo:
        """
        Batalha 3x3 entre dois treinadores. O treinador DESAFIADO ataca
        primeiro (regra do enunciado). Quando um pokémon cai, o dono
        escolhe automaticamente o próximo disponível dentre os 3 iniciais.
        """
        rng = rng or random
        resultado = ResultadoDuelo()
        resultado.log.append(f"=== Batalha: {desafiante.nome} desafia {desafiado.nome}! ===")

        time_a = list(time_desafiante)  # desafiante
        time_b = list(time_desafiado)   # desafiado

        ativo_a = next((p for p in time_a if p.esta_disponivel()), None)
        ativo_b = next((p for p in time_b if p.esta_disponivel()), None)
        if ativo_a is None or ativo_b is None:
            resultado.log.append("Batalha cancelada: um dos lados não possui pokémons disponíveis.")
            return resultado

        bonus_a = desafiante.xp
        bonus_b = desafiado.xp

        turno = 0
        while turno < max_turnos:
            turno += 1
            # desafiado ataca primeiro
            caido = SistemaBatalha.duelo(ativo_b, ativo_a, bonus_b, bonus_a, rng, resultado.log)
            if caido is ativo_a:
                ativo_a = next((p for p in time_a if p.esta_disponivel()), None)
                if ativo_a is None:
                    resultado.vencedor_treinador = desafiado
                    break
                resultado.log.append(f"{desafiante.nome} envia {ativo_a.apelido}!")

            caido = SistemaBatalha.duelo(ativo_a, ativo_b, bonus_a, bonus_b, rng, resultado.log)
            if caido is ativo_b:
                ativo_b = next((p for p in time_b if p.esta_disponivel()), None)
                if ativo_b is None:
                    resultado.vencedor_treinador = desafiante
                    break
                resultado.log.append(f"{desafiado.nome} envia {ativo_b.apelido}!")
        else:
            resultado.log.append("Limite de turnos atingido -- batalha empatada tecnicamente "
                                  "(considerando vitória de quem causou mais dano total).")

        vencedor_treinador = getattr(resultado, "vencedor_treinador", None)
        if vencedor_treinador is desafiante:
            resultado.log.append(f"{desafiante.nome} venceu a batalha!")
            for p in time_a:
                if p.esta_disponivel():
                    p.registrar_vitoria_batalha(desafiado.xp, rng)
            for p in time_b:
                p.registrar_derrota_batalha(rng)
            desafiante.registrar_vitoria_treinador(desafiado.xp)
        elif vencedor_treinador is desafiado:
            resultado.log.append(f"{desafiado.nome} venceu a batalha!")
            for p in time_b:
                if p.esta_disponivel():
                    p.registrar_vitoria_batalha(desafiante.xp, rng)
            for p in time_a:
                p.registrar_derrota_batalha(rng)
            desafiado.registrar_vitoria_treinador(desafiante.xp)
        resultado.vencedor = vencedor_treinador

        # cada batalha consome 1 unidade de tempo percorrido para ambos os treinadores
        desafiante.distancia_percorrida += 1.0
        desafiado.distancia_percorrida += 1.0
        for p in time_a + time_b:
            p.tick(1.0, rng)

        return resultado
