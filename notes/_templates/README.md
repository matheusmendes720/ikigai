# Discovery Log — Templates

> **Para:** qualquer agente futuro (Claude Code, Hermes, Codex, você mesmo num loop diferente) que esteja executando uma Folha Projeto.
>
> **O que é este diretório:** templates de Discovery Log — o registro append-only do progresso diário durante uma Folha Projeto semanal/mensal.

---

## Os 2 tipos de log (não confundir)

### 📋 backlog.md — "o que fiz/observei/decidi"

**Função:** diário de bordo operacional. Factual, curto, objetivo.
**Tom:** engenheiro que documenta uma decisão técnica.
**Quem escreve:** o agente (ou você) **durante ou logo após** a sessão.

**Esqueleto:**
- O que testei/observei (números, medições, comportamento)
- Que decisão tomei (e por quê — 1-2 frases)
- Que ajuste/programação ficou

**Quando preencher:** após cada sessão significativa (treino, commit, sessão de estudo, etc).

### 🪞 reflexao.md — "o que aprendi sobre o processo"

**Função:** reflexão auto-aplicada sobre o que mudou na cabeça, no processo, na motivação. Subjetivo, narrativo.
**Tom:** diário pessoal honesto.
**Quem escreve:** **você** (não o agente — ou se o agente escrever, marcar como "rascunho" pra você revisar).

**Esqueleto:**
- O que senti hoje nesta sessão
- O que mudou na minha cabeça sobre o projeto
- O que ficou mais/menos claro
- O que NÃO vou fazer (descartar)
- Uma pergunta aberta que ficou

**Quando preencher:** fim de ciclo (semana/mês), não todo dia. Mais reflexivo, menos operacional.

---

## Como USAR (loop completo)

```
1. Folha Projeto (repo/vault) define o FOCO DA SEMANA
         ↓
2. Você (ou agente) EXECUTA durante a semana
         ↓
3. A cada sessão: cria notes/YYYY-MM-DD-<slug>-backlog.md (a partir do template abaixo)
         ↓
4. A cada fim-de-ciclo: cria notes/YYYY-MM-DD-<slug>-reflexao.md (a partir do template abaixo)
         ↓
5. Appenda resumo curto em vault/projetos/<folha-projeto>.md## Discovery Log
         ↓
6. Domingo/último dia: Folha Projeto §6 (Revisão de Fim de Ciclo) decide carry-over
         ↓
7. Folha Norte/Próxima Folha Projeto atualiza baseado no que rolou
```

---

## Naming convention (pra agente futuro não se perder)

```
notes/
├── _templates/                          ← ESTES (você está aqui)
│   ├── README.md (este arquivo)
│   ├── backlog.md.template
│   └── reflexao.md.template
├── 2026-09-21-calistenia-backlog.md     ← instâncias reais (preenchidas)
├── 2026-09-21-calistenia-reflexao.md
├── 2026-09-22-calistenia-backlog.md
└── ...
```

**Slug** = mesmo do Folha Projeto. Ex: Folha Projeto `2026-S39-calistenia-base` → logs viram `2026-09-22-calistenia-base-backlog.md` (ou só `-backlog.md` se você abrevia).

---

## Ligação com o vault

| Onde mora | Função | Quem escreve |
|---|---|---|
| `notes/YYYY-MM-DD-<slug>-backlog.md` | Decisões técnicas/operacionais do dia | Agente (ou você) |
| `notes/YYYY-MM-DD-<slug>-reflexao.md` | Reflexão sobre processo/motivação | Você |
| `vault/projetos/<folha-projeto>.md ## Discovery Log` | Resumo inline (1-3 bullets por dia) | Append direto |
| `vault/00-norte/<folha-norte>.md §5` | Lista de Folhas Projeto ativas | Manual |

**Append-only:** nunca edite logs antigos. Cria-se um NOVO arquivo a cada sessão.

---

## Customizações por perfil (Folha Projeto frontmatter)

| Perfil | Tom do backlog | Tom da reflexão |
|---|---|---|
| `cognitivo` (software/estudo) | "Testei X, decidi Y porque W" | "O que aprendi sobre o problema vs sobre mim" |
| `fisico` (treino/esporte) | "Reps, tempo, RPE, decisão de progressão" | "O que meu corpo disse, o que mudou na motivação" |
| `hibrido` (ex: design + produto) | Mistura dos dois acima | Reflexão sobre tensão criativa/produtiva |

Folha Projeto define o `perfil_de_uso` no frontmatter; isso guia o tom dos logs.

---

## Instrução para agente futuro (copy-paste)

```
You are executing a Folha Projeto semanal (path: vault/projetos/<YYYY-Sww>-<slug>.md).
Your job for THIS session:

1. Read the Folha Projeto to understand the FOCO REDUZIDO (2-4 tópicos)
2. Execute the session (whatever the work is)
3. AT THE END of the session, create:
   - notes/YYYY-MM-DD-<slug>-backlog.md (using _templates/backlog.md.template)
   - Append a 1-3 bullet summary to vault/projetos/<folha-projeto>.md ## Discovery Log
4. IF this is the end of the cycle (last session of the week):
   - Also create notes/YYYY-MM-DD-<slug>-reflexao.md (using _templates/reflexao.md.template)

Both templates have explicit INTENT and INSTRUCTIONS at the top — read them BEFORE writing.

DO NOT invent content. If the session was empty, write "sessão vazia — sem progresso observável".
DO NOT edit old logs. Always create a new file per session.
DO NOT mix backlog and reflexao. They serve different purposes.
```

---

## Onde mora o META-NP que justifica isso

- `vault/drafts/folha-norte-projeto-META-v3-interseccao.md` §3.1 (Folha Projeto repo template)
- `code-docs/specs/2026-09-21-spec-META-NP-folha-norte-projeto.md` §5.3 (Discovery Log seção)
- `vault/drafts/folha-norte-projeto-META-INDEX.md` (hub de navegação)