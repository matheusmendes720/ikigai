# PAV Learning Map — Design (2026-07-03)

> **Goal:** um tour guiado em camadas do `operational/` workspace, em modo estudo puro
> (sem bug, sem feature, sem prazo). Saída: tours guiados no chat + mapa persistente
> consolidado ao final.

---

## 1. Contexto

O usuário está com **débito cognitivo** na manutenção do PAV, especificamente:

- Não consegue dar manutenção porque não começou pelas interfaces — construiu pela
  especificação mental do output final e se perdeu no caminho.
- Não entende quase nada de **Typer** (paleta de comandos), **Rich** (rendering), nem
  **Textual** (TUI). Background: aplicações `__main__` rodando no VS Code; agora migrou
  100% para terminal, agravando a fricção.
- Tem LLMs acelerando o processo, o que **potencializa pontos fracos** como gargalo humano
  (não sabe ler o código que está sendo gerado).
- Não consegue criticar a modelagem matemática nem debugar algoritmos do backend.
- Quer documentação de engenharia das interfaces CLI/TUI e das particularidades das
  bibliotecas.

**Intenção declarada:** "estudo profundo para entender de verdade" (objetivo: compreensão,
não entrega imediata).

## 2. Escopo

### Em escopo
- **3 tours guiados** sequenciais no chat (A → B → C):
  - **A. Tour de Boot (CLI paleta)** ← *esta parte, foco imediato*
  - **B. Tour por verbos** (rastreamento invocação → disco)
  - **C. Tour do backend matemático** (H(t), QHE, FSM 4 regimes)
- **1 mapa persistente** consolidado ao final: `docs/2026-MM-DD-pav-learning-map.md`
  com índice navegável, diagrama do grafo de comandos, mapeamento arquivo↔verbo.

### Fora de escopo
- Não vamos ler o repo inteiro. Cada tour lê o estritamente necessário.
- Não vamos explicar Pydantic v2 genericamente — explicamos quando aparece.
- Não vamos rodar `pav --help` durante os tours (usuário pode fazer em paralelo).
- Não vamos cobrir Textual nem Typer callbacks (deixa pra Parte B se houver demanda).
- Não vamos criar arquivos `.md` na raiz (CLAUDE.md invariante: `docs/`).

## 3. Decisões de design

### D1 — Ordem dos tours
A → B → C.

**Por quê:** A (boot linear) dá a chave de leitura — depois disso, qualquer arquivo do
repo é legível. B (tour por verbos) valida a chave com uso real. C (backend matemático)
é a base conceitual que conecta tudo.

### D2 — Formato
Híbrido: tour guiado no chat (alto engajamento) + mapa persistente ao final (memória
externa pra daqui a 2 meses). Custo duplicado; ganho cumulativo.

### D3 — Exercícios integrados
Cada tour inclui 1 exercício curto de leitura (trecho no chat → usuário explica o que
faz). Ativo > passivo. Sem feedback bloqueante se o usuário errar — eu confirmo e sigo.

### D4 — Camadas isoladas
Cada tour tem critério de sucesso explícito (ex.: "saiba ler `app.py` linha por linha em
30s"). Critério claro evita sobre-escopo e dá ao usuário pontos de parada.

### D5 — Pergunta de fundação adiada
O usuário pediu, no fim da aprovação: "começar por esse nome PAV — o que é, e por que
demos esse nome". Resposta vem **depois do design, antes da Parte 1**, porque muda o
ângulo conceitual de tudo que vem depois (PAV = *Produtividade Algorítmica Visual*,
não "ferramenta qualquer").

## 4. Estrutura do tour Parte 1

| # | Arquivo | O que se entende ao final |
|---|---------|----------------------------|
| 0 | Resposta à pergunta-título: "O que é PAV e por que demos esse nome" | Contexto semântico, ângulo conceitual |
| 1 | `apps/cli/src/operational/cli/__init__.py` | O que o `pav` binário importa primeiro |
| 2 | `apps/cli/pyproject.toml` (entry points) | Como `pav`, `pav-os`, `operational` viram 3 nomes pro mesmo código |
| 3 | `apps/cli/src/operational/cli/app.py` | `typer.Typer()` raiz, callback global, `add_typer` × 13 |
| 4 | `commands/<x>_cmd.py` (3 exemplos) | Padrão `app = typer.Typer()` + `@app.command()` |
| 5 | `commands/routine_cmd.py` | Sub-typer com argumentos posicionais + Enums |
| 6 | `commands/analytics_cmd.py` | Sub-typer com callback próprio + multi-flag |
| 7 | `commands/demo_cmd.py` | Sub-typer que chama subprocessos (recursão CLI→CLI) |
| 8 | `console.py` + `services.py` | Os 2 singletons que todo comando usa |
| 9 | `state.py` (top 100 linhas) | Como o estado é construído e exposto |
| 10 | Exercício de leitura | Trecho no chat → usuário explica o que faz |

**Critério de sucesso da Parte 1:** o usuário consegue abrir QUALQUER `commands/<x>_cmd.py`
cold e dizer em 30s (a) que verbos define, (b) quais opções, (c) quais entidades toca,
(d) se é destrutivo.

## 5. Estrutura do mapa persistente (Parte 3)

Ao final dos 3 tours, consolidar `docs/2026-MM-DD-pav-learning-map.md` com:

- Diagrama ASCII do grafo de 13 sub-typers.
- Tabela mapeando cada verbo CLI → arquivo → função.
- Glossário de termos do domínio (QHE, regime, histerese, T1-T9, etc.).
- Índice de "se eu quero mudar X, onde mexo" (matriz intenção→arquivo).
- Lista dos arquivos que o usuário NÃO precisa ler pra manter (categoria "razoável
  ignorar").

## 6. Estrutura dos tours Parte 2 e 3 (apenas referência, não escopo imediato)

**Parte 2 — Tour por verbos (prevista):** pegar 4 comandos representativos
(`routine create`, `habit create`, `demo seed`, `state show`) e rastrear cada um da
invocação ao disco. Exercícios: prever saída; editar uma constante e observar.

**Parte 3 — Tour do backend matemático (prevista):** ler `core/habit_engine.py` e
`core/policy_engine.py` como cartas de algoritmo. Exercício: calcular QHE no papel pra
um conjunto de dados hipotético e comparar com a saída de `compute_qhe()`.

## 7. Não-objetivos

- Não migrar pra framework diferente. Não refatorar. Não consertar bugs.
- Não expandir pra `vibe-ops/` ou outros workspaces.
- Não escrever testes novos (estes tours são leitura + compreensão).
- Não criar dependências novas.

## 8. Sinal de pronto

Quando o usuário disser "ok, próximo tour" / "parte 2" / análogo, parto pra Parte 2.
Se disser "para, vai pro mapa", consolido o que temos até aqui.
