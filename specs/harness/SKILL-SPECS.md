# Skill Specs — rotinas de usabilidade do harness canônico

Status: **specification** (2026-11-01). Cada skill é um contrato executável:
gatilho, entradas, saídas, passos, invariantes e critério de falha. Um agente
de nuvem deve conseguir implementá-los a partir deste arquivo, sem acesso ao
PC do dono.

Formato de cada spec:

```
### <skill-id>
Gatilho:   quando o agente deve ativá-la
Entrada:   o que consome
Saída:     o que entrega (formato exato)
Passos:   numbered
Invariantes: o que NÃO pode quebrar
Falha:     o que fazer quando não dá
```

---

### vault-ingest
Gatilho:   sync do vault para o store, após qualquer escrita em `vault/`.
Entrada:   `vault/` (markdown), store Postgres serverless.
Saída:     `SyncReport` JSON — `{scanned, created, updated, unchanged, skipped[]}`.
Passos:
1. Percorrer `vault/**/*.md`, ignorando `README.md` e `99-archive/`.
2. Classificar cada arquivo em kind + quarter pela árvore `closing-2026/`.
3. Calcular `body_hash` (sha256) e comparar com o artefato existente.
4. Gravar via `WriteRequest` idempotente, com `expected_revision`.
5. Acumular falhas por arquivo em `skipped` sem abortar o lote.
Invariantes: idempotente; identidade estável por caminho; `created`+`updated`
             nunca duplica o mesmo artefato.
Falha:     store indisponível → erro com `store_unavailable`; nada é escrito.

### artifact-update
Gatilho:   um artefato do vault mudou de conteúdo.
Entrada:   caminho do arquivo + store.
Saída:     artefato atualizado com `revision` incrementada e `updated_at` novo.
Passos:
1. Ler e hashear o conteúdo novo.
2. Localizar pelo uid derivado do caminho (não pelo hash de conteúdo).
3. Se `body_hash` igual → devolver `unchanged`, sem escrever.
4. Senão `WriteRequest` com `expected_revision` da versão atual.
Invariantes: o uid não muda quando o conteúdo muda; conflito de revisão é
             propagado ao chamador.
Falha:     revisão divergente → `conflict`; não forçar escrita.

### contract-drift-check
Gatilho:   antes de qualquer commit que toque `src/contracts/`.
Entrada:   árvore de contratos + suite de drift.
Saída:     lista de invariantes verificadas (`ok`/`violated`) e diff de
           contrato quando houver.
Passos:
1. Rodar a suíte de drift (`src/ikigai/.venv` + pytest).
2. Comparar o diff de `src/contracts/` contra os contratos públicos.
3. Se um modelo foi redefinido fora de `src/contracts/` → violação.
Invariantes: nenhum teste de drift removido; testes de drift são append-only.
Falha:     suíte vermelha → bloquear o commit e reportar o primeiro erro.

### deploy-preflight
Gatilho:   antes de promover um commit para o remoto canônico.
Entrada:   commit candidato + ambiente alvo.
Saída:     veredito `PASS`/`FAIL` + primeira violação + caminho do arquivo.
Passos:
1. Conferir escopo canônico (nada de TUI/MCP stdio/harness antigo).
2. Varredura de segredos no diff e no histórico tocado.
3. Suite canônica verde no interpretador do projeto.
4. Migrações do store presentes e versionadas.
Invariantes: o remote recebe apenas código e conteúdo canônicos.
Falha:     qualquer violação → FAIL, sem correção automática silenciosa.

### loop-phase-advance
Gatilho:   o loop terminou uma fase do roadmap.
Entrada:   `.claude/loop/roadmap.md`, `.claude/loop/tasks.md`, `.claude/loop/constitution.md`.
Saída:     próximo marco com `STATUS` atualizado e a fase proposed written.
Passos:
1. Verificar o critério de aceitação do marco atual.
2. Marcar `STATUS: DONE` apenas com verificação registrada.
3. Acrescentar o próximo marco; nunca apagar marcos.
4. Mudança em AGENTS.md/CLAUDE.md → proposta em `docs/`, merge humano.
Invariantes: constitution.md só muda por decisão humana; roadmap é append-only.
Falha:     critério não verificado → o marco continua aberto; nada é pulado.

### vault-decision-note
Gatilho:   o owner tomou uma decisão de produto/arquitetura.
Entrada:   a frase literal da decisão do owner + contexto.
Saída:     `vault/ikigai/decisions/<data>-<slug>.md` com frontmatter e seção
           de consequências e pendências.
Passos:
1. Registrar a frase literal do owner como citação.
2. Linkar ADR, roadmap e tasks relacionados.
3. Listar o que sai/entra do escopo published.
4. Listar pendências que dependem de ação do owner (ex.: rotação de chaves).
Invariantes: append-only; frontmatter obrigatório; decisão nunca inferida.
Falha:     sem frase do owner → não escrever; pedir a decisão.
