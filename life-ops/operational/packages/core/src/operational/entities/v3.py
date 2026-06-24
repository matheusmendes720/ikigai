"""V3 entities — DayContext, DailyReflection, LunchRecord, TransicaoRegistrada.

These entities implement the spec PAV V3 §2 (Data Classes) and §3
(Transitions & Rituals). They extend the base system to cover:

* ``DayContext`` — daily context (TipoDia, orçado vs realizado)
* ``DailyReflection`` — OKRs V3 (parar/repetir/big_win/funcao_rotina/deu_certo/deu_errado/aprendizado)
* ``LunchRecord`` — lunch eat (5min) + rest (30min) + pesado flag
* ``TransicaoRegistrada`` — T1-T9 transitions with completion flag

All entities are Pydantic v2 BaseModel with frozen/immutable semantics
where appropriate.
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field

from operational.enums import (
    EstadoPsicomatico,
    RitualType,
    TipoDia,
)
from operational.types import UEID  # noqa: TC001

__all__ = [
    "DailyReflection",
    "DayContext",
    "LunchRecord",
    "TransicaoRegistrada",
]


# ---------------------------------------------------------------------------
# DayContext — classifica o dia e o orçamento
# ---------------------------------------------------------------------------


class DayContext(BaseModel):
    """Daily context — tipo de dia, orçamento, realizado, desvio (PAV V3 §2).

    Attributes:
        id: UEID no formato ``"ctx_YYYY_MM_DD"``.
        date: Data local do dia.
        tipo_dia: Tipo do dia (CURSO / LIVRE / HARDCORE / DESCANSO).
        hardwork_orcado_min: Hardwork orçado em minutos (do budget).
        hardwork_realizado_min: Hardwork realizado (calculado).
        pomodoros_meta: Meta de pomodoros do dia.
        pomodoros_realizados: Pomodoros completados.
        tem_curso: Flag explícita de curso SENAI no dia.
        tem_deadline: Flag de deadline crítico.
        observacoes: Notas livres sobre o contexto.
        created_at: Timestamp de criação.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    id: UEID
    date: date
    tipo_dia: TipoDia = TipoDia.CURSO
    hardwork_orcado_min: Annotated[int, Field(ge=0, le=1440)] = 240
    hardwork_realizado_min: Annotated[int, Field(ge=0, le=1440)] = 0
    pomodoros_meta: Annotated[int, Field(ge=0, le=24)] = 0
    pomodoros_realizados: Annotated[int, Field(ge=0, le=24)] = 0
    tem_curso: bool = False
    tem_deadline: bool = False
    observacoes: Annotated[str, Field(default="", max_length=500)] = ""
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def desvio_min(self) -> int:
        """Diferença realizado - orçado. Positivo = estourou, negativo = abaixo.

        Returns:
            int: Desvio em minutos.
        """
        return self.hardwork_realizado_min - self.hardwork_orcado_min

    @computed_field  # type: ignore[prop-decorator]
    @property
    def produtividade_pct(self) -> float:
        """X do plano cartesiano: realizado / orçado × 100.

        Returns:
            float: Produtividade em [0, 100+].
        """
        if self.hardwork_orcado_min == 0:
            return 0.0
        return min(100.0, (self.hardwork_realizado_min / self.hardwork_orcado_min) * 100.0)


# ---------------------------------------------------------------------------
# DailyReflection — OKRs V3 (entrada + saída)
# ---------------------------------------------------------------------------


class DailyReflection(BaseModel):
    """OKRs V3 — reflexão de entrada (manhã) e saída (noite) (PAV V3 §2).

    Capture os OKRs manuais elicitados na spec V3:

    **Entrada (manhã)**:
    * ``parar_de_fazer`` — vícios identificados ontem
    * ``repetir`` — hábitos que funcionaram
    * ``sempre_fazer`` — rituais que viraram indexadores de eficácia
    * ``big_win`` — a única coisa que torna outras mais fáceis/irrelevantes

    **Saída (noite)**:
    * ``deu_certo`` — execução sistemática bem-sucedida
    * ``deu_errado`` — equívocos na tomada de decisão
    * ``maior_aprendizado`` — antítese + síntese do dia
    * ``ajustes_para_amanha`` — modificações concretas

    Attributes:
        id: UEID no formato ``"ref_YYYY_MM_DD"``.
        date: Data local.
        parar_de_fazer: Lista de vícios identificados ontem.
        repetir: Lista de hábitos que funcionaram.
        sempre_fazer: Lista de rituais indexadores de eficácia.
        big_win: A única coisa que torna outras mais fáceis.
        deu_certo: Lista de execuções bem-sucedidas.
        deu_errado: Lista de equívocos.
        maior_aprendizado: O aprendizado do dia.
        ajustes_para_amanha: Ajustes finos.
        estado_geral: Estado psicomático do dia.
        created_at: Timestamp.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    id: UEID
    date: date

    # Entrada (manhã)
    parar_de_fazer: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    repetir: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    sempre_fazer: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    big_win: Annotated[str, Field(default="", max_length=300)] = ""

    # Saída (noite)
    deu_certo: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    deu_errado: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    maior_aprendizado: Annotated[str, Field(default="", max_length=500)] = ""
    ajustes_para_amanha: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)

    # Estado
    estado_geral: EstadoPsicomatico = EstadoPsicomatico.REGULAR

    created_at: datetime


# ---------------------------------------------------------------------------
# LunchRecord — controle de almoço (eat 5min + rest 30min)
# ---------------------------------------------------------------------------


class LunchRecord(BaseModel):
    """Registro de almoço (PAV V3 §2 — Categorias).

    O almoço é uma fronteira crítica:
    * ``eat_min`` deve ser curto (5min ideal)
    * ``rest_min`` deve ser 30min ideal
    * ``pesado`` correlaciona com cochilo além do orçado

    Attributes:
        id: UEID no formato ``"lun_YYYY_MM_DD"``.
        date: Data do almoço.
        eat_min: Minutos gastos comendo.
        rest_min: Minutos descansando.
        pesado: Se o almoço foi pesado (correlaciona com sonolência).
        duracao_total: Calculado (eat + rest).
        within_budget: Se está dentro do orçado (35min padrão).
        notas: Notas livres.
        created_at: Timestamp.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    id: UEID
    date: date
    eat_min: Annotated[int, Field(ge=0, le=120)] = 5
    rest_min: Annotated[int, Field(ge=0, le=180)] = 30
    pesado: bool = False
    notas: Annotated[str, Field(default="", max_length=300)] = ""
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duracao_total(self) -> int:
        """Duração total (eat + rest) em minutos.

        Returns:
            int: Soma de eat + rest.
        """
        return self.eat_min + self.rest_min

    @computed_field  # type: ignore[prop-decorator]
    @property
    def within_budget(self) -> bool:
        """Se o almoço está dentro do orçamento padrão (35min total).

        Returns:
            bool: ``True`` se ``eat_min <= 5`` e ``rest_min <= 30``.
        """
        return self.eat_min <= 5 and self.rest_min <= 30


# ---------------------------------------------------------------------------
# TransicaoRegistrada — T1-T9 (PAV V3 §6)
# ---------------------------------------------------------------------------


class TransicaoRegistrada(BaseModel):
    """Registro de uma transição entre períodos/rotinas (PAV V3 §6).

    As 9 transições canônicas (T1-T9) marcam as fronteiras do dia. Cada
    uma tem um tipo de ritual associado e duração padrão.

    T1 = Sono → Workout        T4 = Lunch → Meditação
    T2 = Workout → Curso       T5 = Curso → Lunch
    T3 = Curso → Hardwork      T6 = Hardwork → Noite
    T7 = Noite → Dormir        T8 = Dormir → Sono Prep
    T9 = Dormir → Acordar (ciclo)

    Attributes:
        id: UEID no formato ``"trn_<T>_<YYYY_MM_DD>"``.
        date: Data local.
        codigo: T1-T9 (string).
        ritual: Tipo do ritual realizado.
        duracao_min: Duração real em minutos.
        completed: Se o ritual foi completado.
        notas: Notas livres.
        created_at: Timestamp.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    id: UEID
    date: date
    codigo: Annotated[str, Field(pattern=r"^T[1-9]$")]
    ritual: RitualType
    duracao_min: Annotated[int, Field(ge=0, le=60)] = 15
    completed: bool = False
    notas: Annotated[str, Field(default="", max_length=300)] = ""
    created_at: datetime
