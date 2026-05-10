# Vibe-Ops Daily Loop Runner
# Executa o ciclo cibernético completo e gera o relatório do dia.

$VIBE_OPS_ROOT = "c:\Users\mathe\code_space\produtividade\life\vibe-ops"
$PYTHON_PATH = "python" # Ajuste se necessário

Write-Host "--- Iniciando Vibe-Ops Daily Loop ---" -ForegroundColor Cyan

# 1. Sincronizar dados do Vault (Obsidian)
Write-Host "[1/3] Indexando Vault..." -ForegroundColor Yellow
& $PYTHON_PATH "$VIBE_OPS_ROOT\src\main.py" sync --vault "c:\Users\mathe\code_space\produtividade\system\knowledge\notes"

# 2. Executar Ciclo Cibernético
Write-Host "[2/3] Executando Ciclo Cibernético..." -ForegroundColor Yellow
& $PYTHON_PATH "$VIBE_OPS_ROOT\src\main.py" run-daily

# 3. Mostrar Status Atual
Write-Host "[3/3] Status do Sistema:" -ForegroundColor Green
& $PYTHON_PATH "$VIBE_OPS_ROOT\src\main.py" status

Write-Host "--- Loop Concluído ---" -ForegroundColor Cyan
