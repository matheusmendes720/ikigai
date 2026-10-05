# Strategics Excerpt — IKIGAi

> Excerpto de regras estratégicas carregadas pelo agent layer em cada cycle.
> Append-only. Edite com cautela. Para a fundamentação completa, ver
> `strategics/Hierarquia de Objetivos.md`, `strategics/Planejamento (Estratégico e Tático).md`
> e `strategics/Modelagem Operacional.md`.

## Prioridades (em ordem)

1. **Vida > Trabalho** — se saúde, sono ou relação piora, pare tudo e recupere antes.
2. **Regime RECOVER > PUSH** — em dúvida entre avançar e descansar, reduza carga.
3. **Deep work > meetings** — 1 hora focada vale mais que 4 horas fragmentadas em calls.
5. **Pequeno > Grande** — 1 task de 30 min entrega mais que 1 task de 4h mal escopada.
4. **Persistência > Inspiração** — repetir o que funciona gera mais resultado que inovar.

## Anti-padrões (evitar)

- **Scope creep** — adicionar feature ou objetivo sem uso real validado.
- **Perfeccionismo em tooling** — drift net > refator cosmético; bash-redirect garbage nunca.
- **Meetings sem agenda** — cancela ou executa, sem meio-termo.
- **Switching de contexto > 3x/dia** — degrada ~40% da produtividade; agrupe similares.
- **Acumular dívida de sono** — recuperar uma noite ruim custa 3x o tempo perdido.

## Regras de decisão

- **Trade-off qualidade vs velocidade**: default = velocidade. *Ship > polish.*
- **Auto-exec**: NEVER (ADR-013). Sempre *propose* + review queue; humano decide.
- **Vault append-only**: nunca deletar. Marque como `archived`/`deprecated` quando obsoleto.

## Notas operacionais

- O agent layer é *planner-only* — não calcula Q_HE, regime_state, vetores ou scoring.
  Toda matemática PAV vive no engine arquivado (`archive/legacy-pav/`).
- Quando o cycle_state estiver zerado (sem sonho/meta ativos), o LLM ainda recebe
  estas regras para que as sugestões não sejam genéricas.
- Idioma-alvo das sugestões: **pt-BR**. Manter tom operacional, não motivacional.