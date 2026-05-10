# Script de Agendamento - Windows (PowerShell)
# Este script cria uma tarefa agendada no Windows para rodar o loop cibernético diariamente.

$WorkingDir = (Get-Item $PSScriptRoot).Parent.FullName
$MainScript = Join-Path $WorkingDir "src\main.py"
$PythonExe = (Get-Command python.exe).Source

Write-Host "[*] Configurando agendamento para Vibe-Ops em: $WorkingDir"
Write-Host "[*] Usando Python: $PythonExe"

# Ação: Executar o loop diário
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "$MainScript run-daily" -WorkingDirectory $WorkingDir

# Gatilho: Diariamente às 05:00 da manhã (ideal para revisar o dia anterior)
$Trigger = New-ScheduledTaskTrigger -Daily -At 5am

# Registro da tarefa
try {
    Register-ScheduledTask -TaskName "VibeOps_Daily_Cybernetics" -Action $Action -Trigger $Trigger -Description "Executa o ciclo diário Target-Sensor-Adjuster do Vibe-Ops" -Force
    Write-Host "[+] Sucesso! Tarefa 'VibeOps_Daily_Cybernetics' registrada para as 05:00 AM diariamente."
} catch {
    Write-Error "[-] Falha ao registrar tarefa. Certifique-se de rodar como Administrador."
}
