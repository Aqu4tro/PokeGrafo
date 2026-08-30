"""Sistema determinístico de duelos, capturas e batalhas 3x3.

As escolhas do jogador entram por funções callback. O motor valida ataques,
substituições, pertencimento das equipes e decisões; a GUI apenas coleta as
respostas. Não há limite de turnos nem resultado empatado.
"""

from __future__ import annotations
import random
from typing import Callable, List, Optional

from models.ataque import Ataque
from models.pokemon import Pokemon
from models.treinador import Treinador

PROB_MAXIMA_ESQUIVA_OU_CRITICO = 0.5
ESCALA_PROB_XP = 100.0

SeletorAtaque = Callable[[Treinador, Pokemon, Pokemon], Ataque]
SeletorSubstituto = Callable[[Treinador, List[Pokemon]], Pokemon]
DecisorDesistencia = Callable[[Treinador, int], bool]
DecisorAbandonoCaptura = Callable[[Treinador, int, Pokemon, Pokemon], bool]


def _probabilidade_por_xp(gap_xp: float) -> float:
    return min(PROB_MAXIMA_ESQUIVA_OU_CRITICO, abs(gap_xp) / ESCALA_PROB_XP)


class ResultadoDuelo:
    def __init__(self):
        self.log: List[str] = []
        self.vencedor: Optional[object] = None
        self.perdedor: Optional[Pokemon] = None
        self.vencedor_treinador: Optional[Treinador] = None
        self.capturado = False
        self.abandonado = False
        self.recusado = False
        self.desistente: Optional[Treinador] = None
        self.turnos = 0


class SistemaBatalha:
    @staticmethod
    def ataque_padrao(_treinador: Treinador, atacante: Pokemon,
                      _defensor: Pokemon) -> Ataque:
        """Estratégia determinística de NPC para escolher um golpe conhecido."""
        return atacante.ataques[0]

    @staticmethod
    def dano_base(atacante: Pokemon, defensor: Pokemon,
                  bonus_xp_atacante: float = 0.0,
                  bonus_xp_defensor: float = 0.0) -> float:
        """Fórmula literal do enunciado: ``max(0, AP efetivo - DP efetivo)``."""
        ap_efetivo = atacante.ap + bonus_xp_atacante
        dp_efetivo = defensor.dp + bonus_xp_defensor
        return max(0.0, ap_efetivo - dp_efetivo)

    @staticmethod
    def bloqueio_mutuo(pokemon_a: Pokemon, pokemon_b: Pokemon,
                       bonus_a: float = 0.0, bonus_b: float = 0.0) -> bool:
        """Indica quando nenhum dos lados pode matematicamente causar dano."""
        return (
            SistemaBatalha.dano_base(pokemon_a, pokemon_b, bonus_a, bonus_b) == 0
            and SistemaBatalha.dano_base(pokemon_b, pokemon_a, bonus_b, bonus_a) == 0
        )

    @staticmethod
    def _validar_ataque(pokemon: Pokemon, ataque: Ataque) -> Ataque:
        if ataque not in pokemon.ataques:
            raise ValueError(f"{pokemon.apelido} não conhece o ataque informado.")
        return ataque

    @staticmethod
    def duelo(atacante: Pokemon, defensor: Pokemon, ataque: Ataque,
              bonus_xp_atacante: float = 0.0, bonus_xp_defensor: float = 0.0,
              rng: Optional[random.Random] = None,
              log: Optional[List[str]] = None) -> Optional[Pokemon]:
        """Executa um ataque escolhido e retorna o Pokémon nocauteado."""
        rng = rng or random
        log = log if log is not None else []
        ataque = SistemaBatalha._validar_ataque(atacante, ataque)
        dano = SistemaBatalha.dano_base(
            atacante, defensor, bonus_xp_atacante, bonus_xp_defensor)
        if dano <= 0:
            log.append(f"{atacante.apelido} usa {ataque.nome}, mas não causa dano.")
            return None
        prob_esquiva = _probabilidade_por_xp(defensor.xp - atacante.xp)
        if rng.random() < prob_esquiva:
            log.append(f"{defensor.apelido} esquiva de {ataque.nome}!")
            return None
        prob_critico = _probabilidade_por_xp(atacante.xp - defensor.xp)
        if rng.random() < prob_critico:
            dano *= 2
            log.append(f"Golpe crítico de {atacante.apelido}!")
        defensor.receber_dano(dano, rng)
        log.append(f"{atacante.apelido} usa {ataque.nome} em {defensor.apelido}: "
                   f"{dano:.1f} de dano (HP {defensor.hp}/100).")
        if not defensor.esta_disponivel():
            log.append(f"{defensor.apelido} ficou inconsciente!")
            return defensor
        return None

    @staticmethod
    def _selecionar_ataque(seletor: SeletorAtaque, treinador: Treinador,
                           atacante: Pokemon, defensor: Pokemon) -> Ataque:
        ataque = seletor(treinador, atacante, defensor)
        return SistemaBatalha._validar_ataque(atacante, ataque)

    @staticmethod
    def tentar_captura(treinador: Treinador, pokemon_treinador: Pokemon,
                       pokemon_selvagem: Pokemon,
                       seletor_ataque: Optional[SeletorAtaque] = None,
                       abandonar: bool = False,
                       decisor_abandono: Optional[DecisorAbandonoCaptura] = None,
                       rng: Optional[random.Random] = None) -> ResultadoDuelo:
        rng = rng or random
        resultado = ResultadoDuelo()
        if abandonar and decisor_abandono is None:
            decisor_abandono = lambda _t, _turno, _aliado, _selvagem: True
        seletor = seletor_ataque or SistemaBatalha.ataque_padrao
        resultado.log.append(f"{treinador.nome} desafia {pokemon_selvagem.apelido} selvagem!")
        while pokemon_selvagem.esta_disponivel() and pokemon_treinador.esta_disponivel():
            resultado.turnos += 1
            if (decisor_abandono and decisor_abandono(
                    treinador, resultado.turnos, pokemon_treinador, pokemon_selvagem)):
                resultado.abandonado = True
                resultado.log.append(
                    f"{treinador.nome} abandonou a captura no turno {resultado.turnos}.")
                break
            hp_antes = pokemon_treinador.hp + pokemon_selvagem.hp
            ataque_s = SistemaBatalha.ataque_padrao(treinador, pokemon_selvagem, pokemon_treinador)
            caido = SistemaBatalha.duelo(
                pokemon_selvagem, pokemon_treinador, ataque_s, 0.0, treinador.xp,
                rng, resultado.log)
            if caido:
                break
            ataque_t = SistemaBatalha._selecionar_ataque(
                seletor, treinador, pokemon_treinador, pokemon_selvagem)
            caido = SistemaBatalha.duelo(
                pokemon_treinador, pokemon_selvagem, ataque_t, treinador.xp, 0.0,
                rng, resultado.log)
            if caido:
                break
            hp_depois = pokemon_treinador.hp + pokemon_selvagem.hp
            if (hp_depois == hp_antes and SistemaBatalha.bloqueio_mutuo(
                    pokemon_treinador, pokemon_selvagem, treinador.xp, 0.0)):
                resultado.abandonado = True
                resultado.log.append(
                    "A captura foi abandonada por bloqueio técnico: nenhum lado pode causar dano.")
                break
        if not pokemon_selvagem.esta_disponivel():
            resultado.capturado = True
            resultado.vencedor = pokemon_treinador
            resultado.perdedor = pokemon_selvagem
            pokemon_treinador.registrar_captura(rng)
            treinador.registrar_captura_bem_sucedida()
            resultado.log.append(f"{pokemon_selvagem.apelido} foi capturado!")
        elif not resultado.abandonado:
            resultado.vencedor = pokemon_selvagem
            resultado.perdedor = pokemon_treinador
        return resultado

    @staticmethod
    def _validar_time(treinador: Treinador, time: List[Pokemon]):
        if len(time) != 3 or len({p.id for p in time}) != 3:
            raise ValueError("Cada treinador deve escolher exatamente três Pokémon distintos.")
        if any(p not in treinador.equipe for p in time):
            raise ValueError("Todos os Pokémon escolhidos devem pertencer ao treinador.")
        if any(not p.esta_disponivel() for p in time):
            raise ValueError("Todos os Pokémon escolhidos devem estar conscientes.")

    @staticmethod
    def _proximo(treinador: Treinador, time: List[Pokemon],
                 seletor: Optional[SeletorSubstituto]) -> Optional[Pokemon]:
        disponiveis = [p for p in time if p.esta_disponivel()]
        if not disponiveis:
            return None
        if treinador.eh_jogador and seletor is None:
            raise ValueError("O jogador deve escolher manualmente o Pokémon substituto.")
        escolhido = seletor(treinador, disponiveis) if seletor else disponiveis[0]
        if escolhido not in disponiveis:
            raise ValueError("Substituição inválida: escolha um Pokémon disponível do time.")
        return escolhido

    @staticmethod
    def batalha_treinadores(
            desafiante: Treinador, desafiado: Treinador,
            time_desafiante: List[Pokemon], time_desafiado: List[Pokemon],
            aceitou: bool,
            seletor_ataque_desafiante: Optional[SeletorAtaque] = None,
            seletor_ataque_desafiado: Optional[SeletorAtaque] = None,
            seletor_substituto_desafiante: Optional[SeletorSubstituto] = None,
            seletor_substituto_desafiado: Optional[SeletorSubstituto] = None,
            decisor_desistencia_desafiado: Optional[DecisorDesistencia] = None,
            rng: Optional[random.Random] = None) -> ResultadoDuelo:
        rng = rng or random
        resultado = ResultadoDuelo()
        SistemaBatalha._validar_time(desafiante, time_desafiante)
        SistemaBatalha._validar_time(desafiado, time_desafiado)
        if not aceitou:
            resultado.recusado = True
            resultado.log.append(f"{desafiado.nome} recusou o desafio.")
            return resultado
        if desafiante.eh_jogador and seletor_ataque_desafiante is None:
            raise ValueError("O jogador desafiante deve escolher seus ataques.")
        if desafiado.eh_jogador and seletor_ataque_desafiado is None:
            raise ValueError("O jogador desafiado deve escolher seus ataques.")
        seletor_a = seletor_ataque_desafiante or SistemaBatalha.ataque_padrao
        seletor_b = seletor_ataque_desafiado or SistemaBatalha.ataque_padrao
        ativo_a = SistemaBatalha._proximo(desafiante, time_desafiante,
                                           seletor_substituto_desafiante)
        ativo_b = SistemaBatalha._proximo(desafiado, time_desafiado,
                                           seletor_substituto_desafiado)
        resultado.log.append(f"=== {desafiante.nome} desafia {desafiado.nome} ===")
        while ativo_a is not None and ativo_b is not None:
            resultado.turnos += 1
            if (decisor_desistencia_desafiado and
                    decisor_desistencia_desafiado(desafiado, resultado.turnos)):
                resultado.desistente = desafiado
                resultado.vencedor_treinador = desafiante
                resultado.log.append(f"{desafiado.nome} desistiu da batalha.")
                break
            hp_antes = ativo_a.hp + ativo_b.hp
            ataque_b = SistemaBatalha._selecionar_ataque(
                seletor_b, desafiado, ativo_b, ativo_a)
            caido = SistemaBatalha.duelo(
                ativo_b, ativo_a, ataque_b, desafiado.xp, desafiante.xp,
                rng, resultado.log)
            if caido is ativo_a:
                xp_derrotado = ativo_a.xp
                ativo_b.registrar_vitoria_batalha(xp_derrotado, rng)
                ativo_a.registrar_derrota_batalha(rng)
                ativo_a = SistemaBatalha._proximo(
                    desafiante, time_desafiante, seletor_substituto_desafiante)
                if ativo_a is None:
                    resultado.vencedor_treinador = desafiado
                    break
                resultado.log.append(f"{desafiante.nome} envia {ativo_a.apelido}.")
            ataque_a = SistemaBatalha._selecionar_ataque(
                seletor_a, desafiante, ativo_a, ativo_b)
            caido = SistemaBatalha.duelo(
                ativo_a, ativo_b, ataque_a, desafiante.xp, desafiado.xp,
                rng, resultado.log)
            if caido is ativo_b:
                xp_derrotado = ativo_b.xp
                ativo_a.registrar_vitoria_batalha(xp_derrotado, rng)
                ativo_b.registrar_derrota_batalha(rng)
                ativo_b = SistemaBatalha._proximo(
                    desafiado, time_desafiado, seletor_substituto_desafiado)
                if ativo_b is None:
                    resultado.vencedor_treinador = desafiante
                    break
                resultado.log.append(f"{desafiado.nome} envia {ativo_b.apelido}.")
            hp_depois = (ativo_a.hp if ativo_a else 0) + (ativo_b.hp if ativo_b else 0)
            if (hp_depois == hp_antes and ativo_a is not None and ativo_b is not None
                    and SistemaBatalha.bloqueio_mutuo(
                        ativo_a, ativo_b, desafiante.xp, desafiado.xp)):
                resultado.desistente = desafiado
                resultado.vencedor_treinador = desafiante
                resultado.log.append(
                    f"Bloqueio técnico sem dano: {desafiado.nome} desiste da batalha.")
                break
        vencedor = resultado.vencedor_treinador
        if vencedor is None:
            raise RuntimeError("A batalha terminou sem vencedor, o que viola as regras.")
        perdedor = desafiado if vencedor is desafiante else desafiante
        vencedor.registrar_vitoria_treinador(perdedor.xp)
        resultado.vencedor = vencedor
        resultado.log.append(f"{vencedor.nome} venceu a batalha!")
        desafiante.tempo_decorrido += 1.0
        desafiado.tempo_decorrido += 1.0
        return resultado
