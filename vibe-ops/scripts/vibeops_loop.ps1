# Vibe-Ops Cybernetic Sync Loop (Windows)
# Executa a sincronização global periodicamente

$IntervalSeconds = 1800 # 30 minutos
$WorkingDir = (Get-Item $PSScriptRoot).Parent.FullName
$PythonExe = "uv" # Usando uv conforme plano de implementação

Write-Host "[*] Iniciando Loop de Sincronização Vibe-Ops..."
Write-Host "[*] Diretório: $WorkingDir"
Write-Host "[*] Intervalo: $IntervalSeconds segundos"

while ($true) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$Timestamp] ⚡ Sincronizando..." -ForegroundColor Cyan
    
    try {
        Set-Location $WorkingDir
        # Executa uv run src/main.py sync
        & $PythonExe run src/main.py sync
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[$Timestamp] ✅ Sincronização concluída." -ForegroundColor Green
        } else {
            Write-Host "[$Timestamp] ❌ Falha na sincronização (Exit Code: $LASTEXITCODE)." -ForegroundColor Red
        }
    } catch {
        Write-Host "[$Timestamp] ⚠️ Erro crítico: $_" -ForegroundColor Yellow
    }
    
    Write-Host "[$Timestamp] 💤 Aguardando próxima rodada..."
    Start-Sleep -Seconds $IntervalSeconds
}
