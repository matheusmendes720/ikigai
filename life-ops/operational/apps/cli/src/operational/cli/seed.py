"""Seed 7 days of PAV V3 mock data — 7 cenários mapeados 1:1 com a spec.

Cenários (em ordem cronológica Seg→Dom):

1. **Padrão Ouro**       — Dia Perfeito (CURSO, 11/12 pomodoros, 0 desvios)
2. **Acordou Tarde**     — Desvio Leve (CURSO, +1h acordar, infracao LEVE)
3. **Hardcore**          — Deadline emergencial (HARDCORE, 4h sono)
4. **Recuperação**       — Pós-hardcore (DESCANSO, 10h sono, tudo leve)
5. **Lunch Pesado**      — Almoço pesado + cochilo (CURSO, infracao MEDIA)
6. **Fim de Semana**     — Livre (LIVRE, 9h hardwork, side-project)
7. **Visita Inesperada** — Interrupção social (LIVRE, jantar tarde)

Cada dia tem DayContext + DailyReflection + LunchRecord + Transicoes T1-T9
além das entidades base (sleep, journal, routines, blocks, pomodoros, etc).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from operational.cli.state import (
    ajustes_finos,
    daily_reflections,
    day_contexts,
    habits,
    journals,
    lunch_records,
    policy_decisions,
    policy_setpoints,
    pomodoros,
    routine_logs,
    routines,
    sleep_records,
    time_blocks,
    transicoes,
)
from operational.entities.ajuste_fino import AjusteFino
from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.policy import PolicyDecision, PolicySetpoints
from operational.entities.pomodoro import PomodoroRound
from operational.entities.routine import Routine, RoutineLog
from operational.entities.time_block import TimeBlock
from operational.entities.v3 import (
    DailyReflection,
    DayContext,
    LunchRecord,
    TransicaoRegistrada,
)
from operational.enums import (
    EstadoPsicomatico,
    HabitCategory,
    Period,
    PolicyState,
    PomodoroState,
    RitualType,
    RoutineType,
    TipoDia,
)
from operational.types import UEID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_today = date.today()


def _d(offset: int) -> date:
    return _today - timedelta(days=offset)


def _dt(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, tzinfo=UTC)


def _to_energy_level(score: int) -> EstadoPsicomatico:
    if score >= 7:
        return EstadoPsicomatico.BOM
    if score >= 5:
        return EstadoPsicomatico.REGULAR
    if score >= 3:
        return EstadoPsicomatico.RUIM
    return EstadoPsicomatico.CRITICO


def _to_energy_input(score: int):
    """Map 1-10 score to EnergyLevel (H/M/L) for PolicyDecision.energy_input."""
    from operational.enums import EnergyLevel
    if score >= 7:
        return EnergyLevel.HIGH
    if score >= 4:
        return EnergyLevel.MEDIUM
    return EnergyLevel.LOW


# ---------------------------------------------------------------------------
# 7 Days — Cenários V3 (1:1 com spec PAV §8)
# ---------------------------------------------------------------------------

SEVEN_DAYS: list[dict[str, Any]] = [
    {
        "name": "Segunda Padrao Ouro",
        "scenario": "Padrao Ouro",
        "tipo_dia": TipoDia.CURSO,
        "sleep": {"bedtime": time(20, 30), "wake_time": time(4, 0), "quality": 9,
                      "deep_pct": 28, "rem_pct": 22, "interruptions": 0,
                      "notes": "Sono reparador. Ciclo completo. Acordei naturalmente."},
        "lunch": {"eat_min": 5, "rest_min": 30, "pesado": False, "notas": "Salada + frango grelhado."},
        "orcado": 240, "realizado": 240, "pomodoros_meta": 12, "pomodoros_done": 11,
        "transicoes_complete": 9,
        "routines": [
            ("Despertar Natural + Hidratacao", Period.MANHA, RoutineType.ENTRY, time(4, 0), time(4, 25)),
            ("Deep Work - Feature JWT", Period.MANHA, RoutineType.CORE, time(4, 30), time(8, 0)),
            ("Review Matinal", Period.MANHA, RoutineType.EXIT, time(8, 0), time(8, 15)),
            ("Code Review + Refatoracao", Period.TARDE, RoutineType.CORE, time(8, 30), time(12, 0)),
            ("Almoco + Descanso", Period.TARDE, RoutineType.TRANSITION, time(12, 0), time(13, 0)),
            ("Documentacao Swagger", Period.TARDE, RoutineType.CORE, time(13, 0), time(17, 0)),
            ("Shutdown + Planejamento", Period.TARDE, RoutineType.EXIT, time(17, 0), time(17, 30)),
            ("Preparar Refeicoes + Arrumar Casa", Period.NOITE, RoutineType.EXIT, time(18, 0), time(20, 0)),
        ],
        "blocks": [
            ("Deep Work - Autenticacao JWT", Period.MANHA, (4, 0), (8, 0)),
            ("Code Review + Refatoracao Rotas", Period.TARDE, (8, 30), (12, 0)),
            ("Documentacao Swagger", Period.TARDE, (13, 0), (17, 0)),
            ("Preparacao Dia Seguinte", Period.NOITE, (18, 0), (20, 0)),
        ],
        "pomodoros_s1_s2_s3": [4, 4, 3],
        "ref_entrada": {
            "parar_de_fazer": ["Dormir apos 21h"],
            "repetir": ["Acordar sem alarme", "Hidratacao logo apos acordar"],
            "sempre_fazer": ["Meditacao 10min antes do deep work"],
            "big_win": "Acordar 1h antes do primeiro compromisso (4h) gera flow state matinal",
        },
        "ref_saida": {
            "deu_certo": ["Feature JWT completa + testada", "Code review encontrou 3 bugs antes do deploy"],
            "deu_errado": ["Sessao 3 reduzida por falta de energia pos-almoco"],
            "maior_aprendizado": "Sono define o dia - qualidade 9 leva a energia 9 e foco 9",
            "ajustes_para_amanha": ["Reduzir meditacao de 15 para 10min para liberar 5min de deep work"],
        },
        "journal_manha": {
            "text": ("**DIA PERFEITO**\n\nAcordei 04:00 naturalmente. Sono 8h Q=9. "
                  "Ritual matinal completo. Pronto para o dia.\n\n"
                  "Sessao 1 (04:30-08:00): 4 rounds de 50min. Feature JWT completa."),
            "energia": 9, "foco": 9, "humor_morning": 5, "humor_evening": 5, "pomodoros": 8,
        },
        "journal_noite": {
            "text": ("**REVISAO NOTURNA**\n\nChecklist 8/8 rotinas. "
                  "11/12 pomodoros. Energia 9/10. Foco 9/10."),
            "energia": 8, "foco": 9, "humor_morning": 5, "humor_evening": 5, "pomodoros": 11,
        },
        "desvios": [],
        "licoes": [
            "Manter hidratacao entre rounds melhora foco na 2a metade da manha.",
            "Acordar sem alarme e o melhor indicador de sono reparador.",
        ],
        "ajustes": [
            (Period.MANHA, -5, "Reduzir meditacao 15 para 10min libera 5min de deep work."),
        ],
        "policy": (PolicyState.MAINTAIN, "INFO",
                   "Dentro do padrao ouro. Manter regime. QHE alto.", 3),
    },
    {
        "name": "Terca com Atraso",
        "scenario": "Desvio Leve",
        "tipo_dia": TipoDia.CURSO,
        "sleep": {"bedtime": time(21, 30), "wake_time": time(5, 30), "quality": 6,
                      "deep_pct": 18, "rem_pct": 20, "interruptions": 2,
                      "notes": "Dormi mais tarde (serie no streaming). Acordei 1h alem do padrao ouro."},
        "lunch": {"eat_min": 5, "rest_min": 30, "pesado": False, "notas": "Almoco normal."},
        "orcado": 240, "realizado": 180, "pomodoros_meta": 8, "pomodoros_done": 6,
        "transicoes_complete": 7,
        "routines": [
            ("Despertar Tarde + Hidratacao Rapida", Period.MANHA, RoutineType.ENTRY, time(5, 30), time(5, 45)),
            ("Deep Work Reduzido", Period.MANHA, RoutineType.CORE, time(5, 50), time(8, 0)),
            ("Transicao Acelerada", Period.MANHA, RoutineType.EXIT, time(8, 0), time(8, 5)),
            ("Correcao de Bugs", Period.TARDE, RoutineType.CORE, time(8, 30), time(12, 0)),
            ("Tarefas Atrasadas", Period.TARDE, RoutineType.CORE, time(13, 0), time(16, 0)),
            ("Review + Compensacao", Period.TARDE, RoutineType.EXIT, time(16, 0), time(16, 30)),
            ("Jantar Tarde + Preparacao", Period.NOITE, RoutineType.EXIT, time(18, 30), time(20, 30)),
        ],
        "blocks": [
            ("Deep Work Reduzido (2h)", Period.MANHA, (5, 50), (8, 0)),
            ("Correcao de Bugs Urgentes", Period.TARDE, (8, 30), (12, 0)),
            ("Tarefas Atrasadas", Period.TARDE, (13, 0), (16, 0)),
            ("Jantar + Compensacao", Period.NOITE, (18, 30), (20, 30)),
        ],
        "pomodoros_s1_s2_s3": [2, 2, 2],
        "ref_entrada": {
            "parar_de_fazer": ["Assistir serie apos 19h"],
            "repetir": ["Hidratacao logo ao acordar"],
            "sempre_fazer": ["Higiene sono (sem telas 2h antes)"],
            "big_win": "Ja estar na mesa as 5:50, mesmo apos atraso, reduz o impacto total.",
        },
        "ref_saida": {
            "deu_certo": ["Cumpri os 2 pomodoros da manha apesar do atraso"],
            "deu_errado": ["Tentei compensar workout a tarde - quebra o ciclo (nao fazer mais)"],
            "maior_aprendizado": "Sono 6h + 1h atraso da energia 7 e foco 7. Funciona, mas com margem minima.",
            "ajustes_para_amanha": ["Dormir 20:00 hoje para recuperar 1h de sono"],
        },
        "journal_manha": {
            "text": ("**DESVIO LEVE**\n\nAcordei 05:30 - 1h alem do padrao ouro. "
                  "Sono leve (Q=6).\nDecisao: pular workout, manter 2 pomodoros da manha."),
            "energia": 7, "foco": 7, "humor_morning": 3, "humor_evening": 4, "pomodoros": 2,
        },
        "journal_noite": {
            "text": ("**LICOES DO DESVIO**\n\n1. Compensar workout a tarde foi erro.\n"
                  "2. Foco em tarefas CRITICAS reduziu impacto.\n"
                  "3. Decisao: dormir 20:00 hoje."),
            "energia": 6, "foco": 6, "humor_morning": 3, "humor_evening": 3, "pomodoros": 6,
        },
        "desvios": [
            "Acordei 1h alem do padrao (5:30 vs limite 5:00). Infracao LEVE.",
        ],
        "licoes": [
            "Nao compensar workout a tarde - quebra o ciclo circadiano.",
            "Sono 6h = energia funcional mas com margem apertada.",
        ],
        "ajustes": [
            (Period.NOITE, 60, "Dormir 20:00 hoje (vs 21:30 ontem) para recuperar 1h sono."),
        ],
        "policy": (PolicyState.REDUCE, "WARNING",
                   "Desvio leve mas recuperavel. Recomendar sono extra.", 1),
    },
    {
        "name": "Quarta Hardcore",
        "scenario": "Modo Hardcore",
        "tipo_dia": TipoDia.HARDCORE,
        "sleep": {"bedtime": time(2, 0), "wake_time": time(6, 0), "quality": 4,
                      "deep_pct": 12, "rem_pct": 15, "interruptions": 1,
                      "notes": "Deadline do relatorio trimestral. Dormi so 4h. Cafe as 2h30."},
        "lunch": {"eat_min": 10, "rest_min": 20, "pesado": False,
                      "notas": "Almoco rapido, sem descanso - modo emergencia."},
        "orcado": 660, "realizado": 480, "pomodoros_meta": 11, "pomodoros_done": 8,
        "transicoes_complete": 6,
        "routines": [
            ("Acordar com Cafe Forte", Period.MANHA, RoutineType.ENTRY, time(6, 0), time(6, 10)),
            ("Deep Work Emergencial", Period.MANHA, RoutineType.CORE, time(6, 15), time(11, 0)),
            ("Pausa Estendida 15min", Period.MANHA, RoutineType.TRANSITION, time(11, 0), time(11, 15)),
            ("Continuacao Relatorio", Period.TARDE, RoutineType.CORE, time(11, 15), time(15, 0)),
            ("Almoco Relampago", Period.TARDE, RoutineType.TRANSITION, time(15, 0), time(15, 30)),
            ("Finalizacao + Entrega", Period.TARDE, RoutineType.CORE, time(15, 30), time(17, 0)),
            ("Shutdown Minimo", Period.TARDE, RoutineType.EXIT, time(17, 0), time(17, 15)),
        ],
        "blocks": [
            ("Deep Work Emergencial", Period.MANHA, (6, 15), (11, 0)),
            ("Continuacao Relatorio", Period.TARDE, (11, 15), (15, 0)),
            ("Almoco Relampago", Period.TARDE, (15, 0), (15, 30)),
            ("Finalizacao + Entrega", Period.TARDE, (15, 30), (17, 0)),
        ],
        "pomodoros_s1_s2_s3": [3, 3, 2],
        "ref_entrada": {
            "parar_de_fazer": ["Subestimar deadlines"],
            "repetir": ["Cafe estrategico as 2:30h para reduzir sonolencia"],
            "sempre_fazer": ["Power nap 20min se necessario"],
            "big_win": "Adrenalina da deadline segurou o foco 3h seguidas.",
        },
        "ref_saida": {
            "deu_certo": ["Relatorio entregue as 16:55 (5min antes)"],
            "deu_errado": ["Recuperei pouco - sono acumulado vai cobrar"],
            "maior_aprendizado": "4h sono e sustentavel para 1 dia, mas cobra na proxima 48h.",
            "ajustes_para_amanha": ["RECUPERACAO OBRIGATORIA - dormir 18h hoje"],
        },
        "journal_manha": {
            "text": ("**MODO HARDCORE ATIVADO**\n\nDormi 02:00 ate 06:00 = 4h. Q=4. "
                  "Cafe as 2:30. Adrenalina da deadline.\nEnergia 4, foco 7."),
            "energia": 4, "foco": 5, "humor_morning": 2, "humor_evening": 4, "pomodoros": 3,
        },
        "journal_noite": {
            "text": ("**RELATORIO ENTREGUE**\n\n16:55h, 5min antes do deadline. "
                  "8/11 pomodoros. Sono cobrado.\n"
                  "RECUPERACAO OBRIGATORIA: dormir 18:00h hoje."),
            "energia": 3, "foco": 4, "humor_morning": 2, "humor_evening": 3, "pomodoros": 8,
        },
        "desvios": [
            "Sono 4h. Infracao GRAVE se repetida (max 2x/mes).",
            "Almoco reduzido (5min eat + 20min rest vs 5+30 padrao).",
        ],
        "licoes": [
            "Adrenalina + deadline seguram foco 3h.",
            "1 hardcore/mes e o teto. 2x/mes ja cobra.",
        ],
        "ajustes": [
            (Period.NOITE, 180, "RECUPERACAO: dormir 18:00h hoje (9h sono compensatorio)."),
        ],
        "policy": (PolicyState.RECOVER, "CRITICAL",
                   "Hardcore day. Recuperacao 48h obrigatoria.", 1),
    },
    {
        "name": "Quinta Recuperacao",
        "scenario": "Recuperacao",
        "tipo_dia": TipoDia.DESCANSO,
        "sleep": {"bedtime": time(20, 0), "wake_time": time(6, 0), "quality": 10,
                      "deep_pct": 32, "rem_pct": 25, "interruptions": 0,
                      "notes": "Dormi 18:00 ate 06:00 = 10h. Sono restaurador. Q=10."},
        "lunch": {"eat_min": 5, "rest_min": 30, "pesado": False, "notas": "Almoco leve + leitura."},
        "orcado": 120, "realizado": 90, "pomodoros_meta": 4, "pomodoros_done": 3,
        "transicoes_complete": 7,
        "routines": [
            ("Acordar Sem Pressa", Period.MANHA, RoutineType.ENTRY, time(6, 0), time(6, 30)),
            ("Refatoracao Leve", Period.MANHA, RoutineType.CORE, time(6, 30), time(8, 0)),
            ("Alongamento + Leitura", Period.MANHA, RoutineType.EXIT, time(8, 0), time(8, 30)),
            ("Code Review Local", Period.TARDE, RoutineType.CORE, time(8, 30), time(12, 0)),
            ("Almoco Tranquilo", Period.TARDE, RoutineType.TRANSITION, time(12, 0), time(12, 35)),
            ("Documentacao Opcional", Period.TARDE, RoutineType.CORE, time(13, 0), time(15, 0)),
            ("Shutdown Suave", Period.TARDE, RoutineType.EXIT, time(15, 0), time(15, 30)),
        ],
        "blocks": [
            ("Refatoracao Leve", Period.MANHA, (6, 30), (8, 0)),
            ("Code Review Local", Period.TARDE, (8, 30), (12, 0)),
            ("Documentacao Opcional", Period.TARDE, (13, 0), (15, 0)),
        ],
        "pomodoros_s1_s2_s3": [2, 1, 0],
        "ref_entrada": {
            "parar_de_fazer": ["Ignorar sono de recuperacao"],
            "repetir": ["Acordar sem alarme apos sono longo"],
            "sempre_fazer": ["Dormir 18h apos dia hardcore"],
            "big_win": "10h sono = corpo restaurado para a semana.",
        },
        "ref_saida": {
            "deu_certo": ["Nada de extenuante. Recuperei a energia."],
            "deu_errado": ["Quase forcei um pomodoro extra - parei no tempo."],
            "maior_aprendizado": "Descanso e produtividade armazenada.",
            "ajustes_para_amanha": ["Voltar ao padrao curso amanha"],
        },
        "journal_manha": {
            "text": ("**RECUPERACAO**\n\nDormi 18h ate 4am = 10h. Q=10. "
                  "Acordei restaurado. Energia 8.\nHoje: 2-3 pomodoros apenas."),
            "energia": 8, "foco": 6, "humor_morning": 5, "humor_evening": 5, "pomodoros": 2,
        },
        "journal_noite": {
            "text": ("**DIA SUAVE**\n\n3 pomodoros. Nada forcado. "
                  "Energia recuperada para amanha."),
            "energia": 7, "foco": 5, "humor_morning": 5, "humor_evening": 5, "pomodoros": 3,
        },
        "desvios": [],
        "licoes": [
            "Descanso e produtividade armazenada.",
            "Sono 10h = energia 8 imediata (vs 4h sono = energia 4).",
        ],
        "ajustes": [],
        "policy": (PolicyState.MAINTAIN, "INFO",
                   "Recuperacao OK. Manter ritmo leve.", 1),
    },
    {
        "name": "Sexta Lunch Pesado",
        "scenario": "Lunch Estendido",
        "tipo_dia": TipoDia.CURSO,
        "sleep": {"bedtime": time(20, 30), "wake_time": time(4, 0), "quality": 8,
                      "deep_pct": 24, "rem_pct": 21, "interruptions": 0,
                      "notes": "Sono OK. Acordei no horario. Energia 8."},
        "lunch": {"eat_min": 10, "rest_min": 60, "pesado": True,
                      "notas": "Feijoada pesada. Cochilei 30min alem do orcado. 60min total."},
        "orcado": 240, "realizado": 210, "pomodoros_meta": 8, "pomodoros_done": 7,
        "transicoes_complete": 7,
        "routines": [
            ("Despertar + Hidratacao", Period.MANHA, RoutineType.ENTRY, time(4, 0), time(4, 20)),
            ("Deep Work Manha", Period.MANHA, RoutineType.CORE, time(4, 30), time(7, 30)),
            ("Transicao", Period.MANHA, RoutineType.EXIT, time(7, 30), time(7, 45)),
            ("Code Review", Period.TARDE, RoutineType.CORE, time(8, 0), time(11, 30)),
            ("Almoco PESADO + Cochilo", Period.TARDE, RoutineType.TRANSITION, time(12, 0), time(13, 10)),
            ("Recuperacao Pos-cochilo", Period.TARDE, RoutineType.TRANSITION, time(13, 10), time(13, 30)),
            ("Deep Work Tarde (reduzido)", Period.TARDE, RoutineType.CORE, time(13, 30), time(16, 30)),
            ("Shutdown + Jantar Leve", Period.TARDE, RoutineType.EXIT, time(16, 30), time(17, 30)),
        ],
        "blocks": [
            ("Deep Work Manha", Period.MANHA, (4, 30), (7, 30)),
            ("Code Review", Period.TARDE, (8, 0), (11, 30)),
            ("Almoco PESADO", Period.TARDE, (12, 0), (13, 10)),
            ("Deep Work Tarde Reduzido", Period.TARDE, (13, 30), (16, 30)),
        ],
        "pomodoros_s1_s2_s3": [3, 2, 2],
        "ref_entrada": {
            "parar_de_fazer": ["Almoco pesado antes de dia de foco"],
            "repetir": ["Refeicao leve ao meio dia"],
            "sempre_fazer": ["Agua antes do almoco"],
            "big_win": "Reconhecer o risco de almoco pesado antes do periodo de foco.",
        },
        "ref_saida": {
            "deu_certo": ["Cumpri code review mesmo com cochilo"],
            "deu_errado": ["Cochilo de 30min alem do orcado. Requer ajuste."],
            "maior_aprendizado": "Almoco pesado custa 30min de produtividade + energia por 2h.",
            "ajustes_para_amanha": ["Preparar almoco mais leve sabado (frango + salada)"],
        },
        "journal_manha": {
            "text": ("**ALERTA: ALMOCO PESADO HOJE**\n\nFeijoada no almoco. "
                  "Ja sei que vou cochilar. Vou antecipar: code review antes do almoco."),
            "energia": 8, "foco": 8, "humor_morning": 4, "humor_evening": 4, "pomodoros": 3,
        },
        "journal_noite": {
            "text": ("**COCHILO CONFIRMADO**\n\n30min alem do orcado. Energia baixa 13-15h. "
                  "Recuperei 15:30. Tarde reduzida.\n"
                  "Causa raiz: almoco pesado. Ajustar amanha."),
            "energia": 5, "foco": 6, "humor_morning": 4, "humor_evening": 4, "pomodoros": 7,
        },
        "desvios": [
            "Lunch extrapolou 35min (60min real, +25min alem). Infracao MEDIA.",
        ],
        "licoes": [
            "Almoco pesado = 30min cochilo garantido. Pre-vencao: almoco leve.",
            "Code review antes do almoco = 1 round a mais no dia.",
        ],
        "ajustes": [
            (Period.TARDE, -30, "Amanha: preparar almoco leve (frango + salada) ja na sexta a noite."),
        ],
        "policy": (PolicyState.REDUCE, "WARNING",
                   "Lunch pesado causou perda de 30min. Ajustar refeicoes.", 1),
    },
    {
        "name": "Sabado Livre",
        "scenario": "Fim de Semana",
        "tipo_dia": TipoDia.LIVRE,
        "sleep": {"bedtime": time(21, 0), "wake_time": time(5, 0), "quality": 9,
                      "deep_pct": 28, "rem_pct": 22, "interruptions": 0,
                      "notes": "Sono otimo. Acordei antes do alarme."},
        "lunch": {"eat_min": 5, "rest_min": 30, "pesado": False, "notas": "Salada + proteina."},
        "orcado": 540, "realizado": 480, "pomodoros_meta": 9, "pomodoros_done": 8,
        "transicoes_complete": 9,
        "routines": [
            ("Acordar + Cafe da Cama", Period.MANHA, RoutineType.ENTRY, time(5, 0), time(5, 20)),
            ("Meditacao + Alongamento", Period.MANHA, RoutineType.ENTRY, time(5, 20), time(5, 50)),
            ("Deep Work - Side Project OSS", Period.MANHA, RoutineType.CORE, time(6, 0), time(11, 0)),
            ("Almoco + Familia", Period.TARDE, RoutineType.TRANSITION, time(12, 0), time(13, 0)),
            ("Deep Work - Features", Period.TARDE, RoutineType.CORE, time(13, 0), time(17, 0)),
            ("Caminhada no Parque", Period.TARDE, RoutineType.EXIT, time(17, 0), time(18, 0)),
            ("Jantar com Familia", Period.NOITE, RoutineType.EXIT, time(18, 0), time(20, 0)),
        ],
        "blocks": [
            ("Deep Work - Side Project OSS", Period.MANHA, (6, 0), (11, 0)),
            ("Almoco + Familia", Period.TARDE, (12, 0), (13, 0)),
            ("Deep Work - Features", Period.TARDE, (13, 0), (17, 0)),
            ("Caminhada Parque", Period.TARDE, (17, 0), (18, 0)),
            ("Jantar Familia", Period.NOITE, (18, 0), (20, 0)),
        ],
        "pomodoros_s1_s2_s3": [4, 4, 0],
        "ref_entrada": {
            "parar_de_fazer": ["Work no fim de semana sem objetivo"],
            "repetir": ["Side project no sabado de manha"],
            "sempre_fazer": ["Caminhada no parque 17h"],
            "big_win": "Sabado e o dia de maxima produtividade E recarga emocional.",
        },
        "ref_saida": {
            "deu_certo": ["Contribuicao OSS aceita", "Feature nova implementada"],
            "deu_errado": ["Quase pulei a caminhada - deu pra encaixar"],
            "maior_aprendizado": "Fim de semana produtivo + recarga emocional = segunda com tanque cheio.",
            "ajustes_para_amanha": ["Domingo: preparacao completa para semana"],
        },
        "journal_manha": {
            "text": ("**FIM DE SEMANA**\n\nSabado. Sem curso. "
                  "Maxima produtividade: side project + features.\nEnergia 9, foco 9."),
            "energia": 9, "foco": 9, "humor_morning": 5, "humor_evening": 5, "pomodoros": 4,
        },
        "journal_noite": {
            "text": ("**DIA PERFEITO**\n\n8 pomodoros. Side project + features. "
                  "Caminhada com sol. Jantar em familia. Recarregado."),
            "energia": 8, "foco": 8, "humor_morning": 5, "humor_evening": 5, "pomodoros": 8,
        },
        "desvios": [],
        "licoes": [
            "Fim de semana pode ser 100% produtivo E recarregante.",
            "Caminhada 17h = quebra natural + beneficio fisico.",
        ],
        "ajustes": [],
        "policy": (PolicyState.PUSH, "INFO",
                   "Sabado excelente. QHE alto. Manter.", 1),
    },
    {
        "name": "Domingo Visita Inesperada",
        "scenario": "Interrupcao Social",
        "tipo_dia": TipoDia.LIVRE,
        "sleep": {"bedtime": time(20, 0), "wake_time": time(5, 0), "quality": 9,
                      "deep_pct": 27, "rem_pct": 23, "interruptions": 1,
                      "notes": "Sono otimo. Acordei 1x durante a noite (vizinho)."},
        "lunch": {"eat_min": 10, "rest_min": 35, "pesado": False,
                      "notas": "Almoco com visita (amigo veio). Mais longo que o normal."},
        "orcado": 540, "realizado": 420, "pomodoros_meta": 9, "pomodoros_done": 7,
        "transicoes_complete": 7,
        "routines": [
            ("Acordar + Meditacao", Period.MANHA, RoutineType.ENTRY, time(5, 0), time(5, 30)),
            ("Deep Work - Preparacao Semana", Period.MANHA, RoutineType.CORE, time(5, 30), time(8, 0)),
            ("Cafe da Manha", Period.MANHA, RoutineType.EXIT, time(8, 0), time(8, 30)),
            ("Deep Work - Review do Plano", Period.TARDE, RoutineType.CORE, time(8, 30), time(12, 0)),
            ("VISITA INESPERADA - Almoço + Café", Period.TARDE, RoutineType.TRANSITION, time(12, 0), time(14, 30)),
            ("Retomada (reduzida)", Period.TARDE, RoutineType.CORE, time(14, 30), time(16, 0)),
            ("Jantar Tarde + Preparacao", Period.NOITE, RoutineType.EXIT, time(19, 0), time(20, 30)),
        ],
        "blocks": [
            ("Deep Work - Preparacao Semana", Period.MANHA, (5, 30), (8, 0)),
            ("Deep Work - Review do Plano", Period.TARDE, (8, 30), (12, 0)),
            ("VISITA INESPERADA", Period.TARDE, (12, 0), (14, 30)),
            ("Retomada Reduzida", Period.TARDE, (14, 30), (16, 0)),
            ("Jantar Tarde", Period.NOITE, (19, 0), (20, 30)),
        ],
        "pomodoros_s1_s2_s3": [3, 2, 2],
        "ref_entrada": {
            "parar_de_fazer": ["Reclamar de visitas - faz parte da vida"],
            "repetir": ["Soneca/meditacao 30min antes de comecar"],
            "sempre_fazer": ["Plano da semana no domingo de manha"],
            "big_win": "Visita inesperada nao destruiu o dia - adaptei e continuei.",
        },
        "ref_saida": {
            "deu_certo": ["Adaptei o plano. Recuperei 14:30."],
            "deu_errado": ["Jantar 19h = luz azul apos 18h. Infracao LEVE."],
            "maior_aprendizado": "Visitas sao parte da vida. Perder 2h nao e perder o dia.",
            "ajustes_para_amanha": ["Reflexao: como evitar visitas surpresa no domingo?"],
        },
        "journal_manha": {
            "text": ("**PLANO DA SEMANA**\n\nDomingo. Revisar tarefas da semana. "
                  "Organizar Taskwarrior. Energia 9, foco 9."),
            "energia": 9, "foco": 9, "humor_morning": 5, "humor_evening": 5, "pomodoros": 3,
        },
        "journal_noite": {
            "text": ("**VISITA INESPERADA**\n\nAmigo chegou 12h. Almoco + cafe ate 14:30. "
                  "Retomei 14:30-16h. Jantar 19h (luz azul apos 18h).\n"
                  "Nao destruiu o dia. Adaptei."),
            "energia": 7, "foco": 6, "humor_morning": 5, "humor_evening": 5, "pomodoros": 7,
        },
        "desvios": [
            "Visita inesperada roubou 2h30 de trabalho. (Imprevisto social, sem infracao).",
            "Jantar 19h = luz azul 1h apos 18h. Infracao LEVE.",
        ],
        "licoes": [
            "Imprevistos sociais sao faceis de absorver com plano previo.",
            "Perder 2h30 nao significa perder o dia - retomar sempre vale a pena.",
        ],
        "ajustes": [
            (Period.NOITE, -60, "Ajustar jantar para 17:30 quando ha visita no domingo."),
        ],
        "policy": (PolicyState.MAINTAIN, "INFO",
                   "Domingo OK. Visita absorvida sem grandes perdas.", 1),
    },
]


# ---------------------------------------------------------------------------
# T1-T9 transitions mapping
# ---------------------------------------------------------------------------

TRANSITIONS: list[tuple[str, RitualType, int]] = [
    ("T1", RitualType.HYDRATION, 15),    # Sono -> Workout
    ("T2", RitualType.MORNING, 15),      # Workout -> Curso
    ("T3", RitualType.MORNING, 15),      # Curso -> Hardwork
    ("T4", RitualType.MEDITATION, 15),   # Lunch -> Meditacao
    ("T5", RitualType.MORNING, 15),      # Curso -> Lunch
    ("T6", RitualType.SHUTDOWN, 30),     # Hardwork -> Noite
    ("T7", RitualType.EVENING, 15),      # Noite -> Dormir
    ("T8", RitualType.EVENING, 15),      # Dormir -> Sono Prep
    ("T9", RitualType.MORNING, 0),       # Dormir -> Acordar
]


# ---------------------------------------------------------------------------
# Seed entry point
# ---------------------------------------------------------------------------


def seed_demo_data() -> str:
    """Populate 7 days of PAV V3 mock data (7 cenarios)."""
    counts: dict[str, int] = {
        "habits": 0, "routines": 0, "blocks": 0, "journals": 0,
        "sleep": 0, "pomodoros": 0, "logs": 0, "ajustes": 0,
        "policies": 0, "day_contexts": 0, "reflections": 0,
        "lunches": 0, "transicoes": 0,
    }

    # Habits (idempotent — check by name)
    DEMO_HABITS: list[dict[str, Any]] = [
        {"name": "Beber 2L de Agua", "category": HabitCategory.PHYSIOLOGICAL, "resistance": 2.0, "weight_in_qhe": 0.8},
        {"name": "Meditar 10min", "category": HabitCategory.RITUAL, "resistance": 3.0, "weight_in_qhe": 0.6},
        {"name": "Alongamento Matinal", "category": HabitCategory.PHYSIOLOGICAL, "resistance": 4.0, "weight_in_qhe": 0.5},
        {"name": "Ler 30min Tecnico", "category": HabitCategory.COGNITIVE, "resistance": 5.0, "weight_in_qhe": 0.7},
        {"name": "Caminhada 20min", "category": HabitCategory.PHYSIOLOGICAL, "resistance": 4.0, "weight_in_qhe": 0.4},
        {"name": "Ligar para Familia", "category": HabitCategory.SOCIAL, "resistance": 6.0, "weight_in_qhe": 0.3},
        {"name": "Escrever no Diario", "category": HabitCategory.CREATIVE, "resistance": 3.0, "weight_in_qhe": 0.4},
        {"name": "Planejar Dia Seguinte", "category": HabitCategory.RITUAL, "resistance": 1.0, "weight_in_qhe": 0.9},
    ]
    for h in DEMO_HABITS:
        existing = habits.list(filters={"name": h["name"]})
        if not existing:
            habit = Habit(
                id=UEID(f"hab_{h['name'].lower().replace(' ', '_')[:20]}"),
                name=h["name"],
                category=h["category"],
                resistance=h["resistance"],
                weight_in_qhe=h["weight_in_qhe"],
                created_at=datetime.now(UTC),
            )
            habits.upsert(habit)
            counts["habits"] += 1

    # Policy setpoints (once)
    if not policy_setpoints.list():
        for state in PolicyState:
            sp = PolicySetpoints.from_pav_defaults(state)
            policy_setpoints.upsert(sp)

    # 7 days
    for i, day in enumerate(SEVEN_DAYS):
        d = _d(6 - i)
        routine_ids: list[str] = []

        # Sleep
        s = day["sleep"]
        sleep_records.upsert(SleepRecord(
            id=UEID(f"sle_demo_{d.strftime('%Y%m%d')}"),
            date=d,
            bedtime=s["bedtime"],
            wake_time=s["wake_time"],
            quality_score=s["quality"],
            deep_sleep_pct=s["deep_pct"],
            rem_sleep_pct=s["rem_pct"],
            interruptions=s["interruptions"],
            notes=s["notes"],
            source="MANUAL",
            created_at=_dt(d, s["wake_time"].hour, s["wake_time"].minute),
        ))
        counts["sleep"] += 1

        # Routines
        for j, r in enumerate(day["routines"]):
            rid = UEID(f"rou_demo_{i:02d}_{j:02d}")
            routine_ids.append(str(rid))
            rname, rperiod, rtype, rstart, rend = r
            routines.upsert(Routine(
                id=rid,
                name=rname,
                period=rperiod,
                routine_type=rtype,
                start_time=rstart,
                end_time=rend,
                description=f"{day['scenario']} - {day['name']}",
                mandatory=True,
                created_at=_dt(d, rstart.hour, rstart.minute),
            ))
            counts["routines"] += 1

        # Time blocks
        for j, b in enumerate(day["blocks"]):
            sh, sm = b[2]
            eh, em = b[3]
            blabel, bperiod, _, _ = b
            time_blocks.upsert(TimeBlock(
                id=UEID(f"blk_demo_{i:02d}_{j:02d}"),
                label=blabel,
                start=_dt(d, sh, sm),
                end=_dt(d, eh, em),
                period=bperiod,
                created_at=_dt(d, sh, sm),
            ))
            counts["blocks"] += 1

        # Routine logs (auto-generate based on day energia/foco)
        avg_energia = day.get("journal_manha", {}).get("energia", 7)
        avg_foco = day.get("journal_manha", {}).get("foco", 7)
        for r_idx, rid_str in enumerate(routine_ids):
            # Vary energia/foco by time of day
            if r_idx < 2:
                e = max(1, min(10, avg_energia + 1))
                f = max(1, min(10, avg_foco + 1))
            elif r_idx < 5:
                e = max(1, min(10, avg_energia))
                f = max(1, min(10, avg_foco))
            else:
                e = max(1, min(10, avg_energia - 1))
                f = max(1, min(10, avg_foco - 1))
            routine_logs.upsert(RoutineLog(
                id=UEID(f"rlg_demo_{i:02d}_{r_idx:02d}"),
                routine_id=UEID(rid_str),
                date=d,
                period=day["routines"][r_idx][1],
                routine_type=day["routines"][r_idx][2],
                text=f"Execucao automatica do cenario {day['scenario']}",
                energia_nivel=e,
                foco_nivel=f,
                humor=4,
                created_at=_dt(d, 22, 0),
            ))
            counts["logs"] += 1

        # Ajustes finos (from day['ajustes'])
        for adj_period, adj_minutos, adj_reason in day.get("ajustes", []):
            ajustes_finos.upsert(AjusteFino(
                id=UEID(f"adj_demo_{i:02d}_{counts['ajustes']:02d}"),
                date=d,
                period=adj_period,
                minutos=adj_minutos,
                reason=adj_reason,
                created_at=_dt(d, 20, 0),
            ))
            counts["ajustes"] += 1

        # Journal entries
        for j, key in enumerate(["journal_manha", "journal_noite"]):
            if key not in day:
                continue
            entry = day[key]
            journals.upsert(JournalEntry(
                id=UEID(f"jrn_demo_{i:02d}_{j:02d}"),
                date=d,
                entry_text=entry["text"],
                energia_nivel=entry["energia"],
                foco_nivel=entry["foco"],
                humor_morning=entry.get("humor_morning"),
                humor_evening=entry.get("humor_evening"),
                pomodoros_completos=entry["pomodoros"],
                periods_covered=set(),
                desvios=day.get("desvios", []),
                licoes_aprendidas=day.get("licoes", []),
                created_at=_dt(d, 20, 0),
            ))
            counts["journals"] += 1

        # Pomodoros
        pm = 0
        for sect_idx, n_rounds in enumerate(day["pomodoros_s1_s2_s3"]):
            for rnd in range(n_rounds):
                start_h = [4, 8, 13][min(sect_idx, 2)]
                pomodoros.upsert(PomodoroRound(
                    id=UEID(f"pom_demo_{i:02d}_{pm:02d}"),
                    round_number=pm + 1,
                    state=PomodoroState.COMPLETE,
                    started_at=_dt(d, start_h + rnd * 1, sect_idx * 10),
                    completed_at=_dt(d, start_h + rnd * 1 + 1, sect_idx * 10),
                    paused_duration_seconds=0,
                ))
                pm += 1
                counts["pomodoros"] += 1

        # DayContext (V3)
        day_contexts.upsert(DayContext(
            id=UEID(f"ctx_demo_{i:02d}"),
            date=d,
            tipo_dia=day["tipo_dia"],
            hardwork_orcado_min=day["orcado"],
            hardwork_realizado_min=day["realizado"],
            pomodoros_meta=day["pomodoros_meta"],
            pomodoros_realizados=day["pomodoros_done"],
            tem_curso=day["tipo_dia"] in (TipoDia.CURSO, TipoDia.HARDCORE),
            tem_deadline=day["tipo_dia"] == TipoDia.HARDCORE,
            observacoes=f"{day['scenario']}: {day['name']}",
            created_at=_dt(d, 4, 0),
        ))
        counts["day_contexts"] += 1

        # DailyReflection (V3)
        ref_entrada = day.get("ref_entrada", {})
        ref_saida = day.get("ref_saida", {})
        (ref_entrada.get("energia", 7) + ref_saida.get("energia", 7)) // 2 if "energia" in ref_entrada else 7
        # We don't track energia in ref dicts - use heuristica from journal
        jm = day.get("journal_manha", {})
        jn = day.get("journal_noite", {})
        avg_energia = ((jm.get("energia", 7) + jn.get("energia", 7)) // 2) if jm and jn else 7
        daily_reflections.upsert(DailyReflection(
            id=UEID(f"ref_demo_{i:02d}"),
            date=d,
            parar_de_fazer=ref_entrada.get("parar_de_fazer", []),
            repetir=ref_entrada.get("repetir", []),
            sempre_fazer=ref_entrada.get("sempre_fazer", []),
            big_win=ref_entrada.get("big_win", ""),
            deu_certo=ref_saida.get("deu_certo", []),
            deu_errado=ref_saida.get("deu_errado", []),
            maior_aprendizado=ref_saida.get("maior_aprendizado", ""),
            ajustes_para_amanha=ref_saida.get("ajustes_para_amanha", []),
            estado_geral=_to_energy_level(avg_energia),
            created_at=_dt(d, 22, 0),
        ))
        counts["reflections"] += 1

        # LunchRecord (V3)
        l = day["lunch"]
        lunch_records.upsert(LunchRecord(
            id=UEID(f"lun_demo_{i:02d}"),
            date=d,
            eat_min=l["eat_min"],
            rest_min=l["rest_min"],
            pesado=l["pesado"],
            notas=l["notas"],
            created_at=_dt(d, 12, l["eat_min"]),
        ))
        counts["lunches"] += 1

        # Transicoes T1-T9 (V3)
        for j, (code, ritual, dur) in enumerate(TRANSITIONS):
            transicoes.upsert(TransicaoRegistrada(
                id=UEID(f"trn_{code.lower()}_{d.strftime('%Y%m%d')}"),
                date=d,
                codigo=code,
                ritual=ritual,
                duracao_min=dur,
                completed=j < day["transicoes_complete"],
                created_at=_dt(d, 8 + j, 0),
            ))
            counts["transicoes"] += 1

        # Policy decision
        pol = day.get("policy")
        if pol:
            sp = PolicySetpoints.from_pav_defaults(pol[0])
            policy_decisions.upsert(PolicyDecision(
                id=UEID(f"pol_demo_{i:02d}"),
                date=d,
                state=pol[0],
                setpoints=sp,
                severity=pol[1],
                rationale=pol[2],
                days_in_state=pol[3],
                infraction_count=len(day.get("desvios", [])),
                energy_input=_to_energy_input(
                    day.get("journal_manha", {}).get("energia", 7)
                ) if day.get("journal_manha") else None,
                created_at=_dt(d, 20, 30),
            ))
            counts["policies"] += 1

    # Build summary
    total = sum(counts.values())
    lines = [
        "🌱 **Demo V3 seeded (7 cenários)!**",
        "",
        "| Entity | Count |",
        "|:-------|:-----:|",
    ]
    for k, v in counts.items():
        lines.append(f"| {k.title()} | {v} |")
    lines.append(f"| **Total** | **{total}** |")
    lines.append("")
    lines.append("Cenários: Padrão Ouro → Acordou Tarde → Hardcore → Recuperação → "
                 "Lunch Pesado → Fim de Semana → Visita Inesperada")
    lines.append("Use `operational report daily --date YYYY-MM-DD` para ver cada cenário.")

    return "\n".join(lines)


def clear_demo_data() -> str:
    """Remove all demo data from all repositories."""
    for repo in [
        routines, routine_logs, time_blocks, journals, habits,
        sleep_records, pomodoros, policy_decisions, policy_setpoints,
        ajustes_finos, day_contexts, daily_reflections, lunch_records, transicoes,
    ]:
        repo.clear()
    for state in PolicyState:
        sp = PolicySetpoints.from_pav_defaults(state)
        policy_setpoints.upsert(sp)
    return "🗑️ All demo data cleared. Setpoints regenerated."


def demo_stats() -> str:
    """Return a stats table of current data."""
    items = [
        ("Routines", len(routines.list())),
        ("Routine Logs", len(routine_logs.list())),
        ("Time Blocks", len(time_blocks.list())),
        ("Journal Entries", len(journals.list())),
        ("Habits", len(habits.list())),
        ("Sleep Records", len(sleep_records.list())),
        ("Pomodoros", len(pomodoros.list())),
        ("Policy Decisions", len(policy_decisions.list())),
        ("Policy Setpoints", len(policy_setpoints.list())),
        ("Ajustes Finos", len(ajustes_finos.list())),
        ("Day Contexts (V3)", len(day_contexts.list())),
        ("Daily Reflections (V3)", len(daily_reflections.list())),
        ("Lunch Records (V3)", len(lunch_records.list())),
        ("Transitions (V3)", len(transicoes.list())),
    ]
    total = sum(v for _, v in items)
    lines = ["| Entity | Count |", "|:-------|:-----:|"]
    for k, v in items:
        lines.append(f"| {k} | {v} |")
    lines.append(f"| **Total** | **{total}** |")
    return "\n".join(lines)
