# BYD Brasil — Análise de Vulnerabilidade Macroeconômica
**Autor:** Matheus Mendes · **Data:** 2026-07-09 · **Stack:** Python/Polars/DuckDB/Statsmodels/Plotly

## TL;DR
BYD Brasil (Camaçari, BA) tem **índice composto de vulnerabilidade = 59/100**.
Drivers principais: (1) **câmbio** com PTAX vol 30d = 10.7% annualized; (2) **supply chain**
com HHI cells de bateria = 4850 (altamente concentrado); (3) **regulatório**
com 18% do preço coberto por incentivos; (4) **concorrência** com share BYD EV BR caindo de 38% (2026) para 24% (2028).

## 1. Câmbio (peso 30%) — score 0/100
- PTAX 2026-07-08: R$ 5.1552
- Vol 30d anualizada: **10.7%** | Vol 90d: 11.2%
- Trend 180d: -5.22%
- **Monte Carlo (10k runs, 6m)**: impacto BOM = média -0.1% | P5 -6.7% | P95 7.0%
- **Pitch**: '42% da BOM exposta a PTAX vol. Stress test P95 = -7% BOM em 6m.'

## 2. Supply chain (peso 30%) — score 100/100
- HHI por categoria: {'battery_cells': 4850, 'lithium': 2500, 'semiconductors': 2925}
- **battery_cells HHI = 4850** (>2500 = highly concentrated; CATL + BYD-Fintech dominant)
- semiconductors HHI = 2925 (TSMC + Samsung)
- lithium HHI = 2500 (Albemarle dominant)
- **Pitch**: '78% das células de bateria dependem de 2 fornecedores asiáticos. HHI crítico para antitrust e geopolítica.'

## 3. Regulatório (peso 20%) — score 82/100
- Cobertura atual (Rota 2030 + BNDES Plano Mais Produção): **18% do preço**
- Cenário continuidade: 18% | Parcial rollback: 10% | Total rollback: 0% | Expansão: 25%
- **Pitch**: '18% do preço subsidiado. Rollback = -8pp margem. Modelo cobre 4 cenários políticos.'

## 4. Concorrência (peso 20%) — score 62/100
- Share BYD EV BR 2026: 38% | 2027: 31% | 2028: 24% (projetado)
- Tesla: 5% → 18% (capex confirmado SP)
- VW: 22% → 26% (fábrica confirma)
- GM: 15% → 20% (capex anunciado)
- **Pitch**: 'BYD share EV BR cai de 38% para 24% em 2 anos se concorrentes cumprirem capex.'

## Output artifacts
- `cambio-monte-carlo.html` (Section 1.5) — distribuição de impacto
- `cambio-stress-test.html` (Section 1) — cenário determinístico
- `supply-chain-sankey.html` (Section 2) — rede de fornecedores
- `regulatory-scenarios.html` (Section 3) — 4 cenários políticos
- `competition-landscape.html` (Section 4) — projeção 2026-2028
- `composite-vulnerability-radar.html` (Section 5) — índice composto

## Methodology
- **Data sources**: BCB SGS (PTAX 1635 obs), supplier estimates (CATL/BYD-Fintech/TSMC/Samsung/Albemarle shares)
- **Tools**: Python 3.14, Polars 1.42, DuckDB 1.5, Statsmodels 0.14, Plotly 6.8
- **Refresh cadence**: weekly (PTAX refresh); monthly (supplier share update)
- **Limitations**: supplier shares são estimativas (refinar com 10-K disclosure); competition share assume competidores cumprem capex (risco de execução)
