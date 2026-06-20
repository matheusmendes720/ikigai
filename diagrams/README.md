# Diagramas do Algorithmic Life OS

Diagramas Mermaid renderizados com [`@mermaid-js/mermaid-cli`](https://github.com/mermaid-js/mermaid-cli).

## Arquivos

| Arquivo | Descrição |
|---|---|
| `topologia.mmd` | Fonte Mermaid — diagrama de topologia do data-mesh |
| `topologia.png` | Renderização PNG (dark mode, 4000×6000) |
| `conceitual.mmd` | Fonte Mermaid — diagrama T→B→S do `CONCEPTUAL_MODEL.md` |
| `conceitual.png` | Renderização PNG do modelo conceitual (dark mode) |
| `cluster_plan.mmd` | Fonte Mermaid — diagrama de capa do `CLUSTER_PLAN.md` |
| `cluster_plan.png` | Renderização PNG do Cluster 1 (rotinas/blocos) |
| `cluster_proj.mmd` | Fonte Mermaid — diagrama de capa do `CLUSTER_PROJ.md` |
| `cluster_proj.png` | Renderização PNG do Cluster 2 (PMO↔TW) |
| `cluster_study.mmd` | Fonte Mermaid — diagrama de capa do `CLUSTER_STUDY.md` |
| `cluster_study.png` | Renderização PNG do Cluster 3 (PKM + pré-req) |
| `cluster_plan_drill.mmd` | Fonte Mermaid — diagrama §4.5 IKIGAi ↔ PAV do `CLUSTER_PLAN.md` |
| `cluster_plan_drill.png` | Renderização PNG do drill-down do Cluster 1 (jornada 3-5h → 21h) |
| `puppeteer-config.json` | Config do Puppeteer (aponta para Chrome local) |

## Como atualizar um diagrama

### 1. Editar a fonte `.mmd`

```vim
:e diagrams/topologia.mmd
" edite o que precisar
:wq
```

### 2. Renderizar PNG

```powershell
$env:PUPPETEER_SKIP_DOWNLOAD="true"
mmdc -i diagrams/topologia.mmd `
     -o diagrams/topologia.png `
     -p diagrams/puppeteer-config.json `
     -t dark -b "#1e1e2e" `
     -w 4000 -H 6000
```

### 3. Abrir para conferir

```powershell
start diagrams/topologia.png
```

## Opções úteis do `mmdc`

| Opção | Exemplo | Descrição |
|---|---|---|
| `-t` / `--theme` | `-t dark` | Tema: `default`, `dark`, `forest`, `neutral` |
| `-b` / `--backgroundColor` | `-b "#1e1e2e"` | Cor de fundo (hex, nome, ou `transparent`) |
| `-w` / `--width` | `-w 4000` | Largura em px |
| `-H` / `--height` | `-H 6000` | Altura em px |
| `-o` / `--output` | `-o saida.png` | Arquivo de saída (png, svg, pdf) |
| `-c` / `--configFile` | (não usado aqui) | Arquivo JSON de config do Mermaid |
| `-p` / `--puppeteerConfigFile` | `-p puppeteer-config.json` | Config do Puppeteer (útil para apontar Chrome instalado) |
| `-C` / `--cssFile` | `-C custom.css` | Arquivo CSS extra injetado na página |

## Dicas

- **Parênteses `( )` e colchetes `[ ]` em labels** precisam de aspas duplas: `-->|"label (com parens)"| B`
- **Se o Puppeteer falhar**, verifique se o Chrome está atualizado no caminho do `puppeteer-config.json`
- **Se o PNG sair cortado**, aumente `-w` e `-H`
- Para **SVG** (editável no Inkscape/Illustrator): troque `-o topologia.png` por `-o topologia.svg`
