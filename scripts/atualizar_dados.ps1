# ==============================================================================
# atualizar_dados.ps1 — Sessão 14
# Wrapper PowerShell para atualizar dados CVM automaticamente.
# Ativar e executar via Task Scheduler ou manualmente:
#   .\scripts\atualizar_dados.ps1
#   .\scripts\atualizar_dados.ps1 -DryRun
# ==============================================================================
param(
    [switch]$DryRun,
    [int[]]$Anos = @()
)

$Root    = Split-Path -Parent $PSScriptRoot
$Venv    = Join-Path $Root ".venv\Scripts\python.exe"
$Script  = Join-Path $Root "scripts\atualizar_todos.py"
$LogDir  = Join-Path $Root "logs"

if (-not (Test-Path $Venv)) {
    Write-Error "Ambiente virtual não encontrado em $Venv. Execute: python -m venv .venv && pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile   = Join-Path $LogDir "atualizar_$Timestamp.log"

$Args = @("--anos")
if ($Anos.Count -gt 0) {
    $Args += $Anos
} else {
    $currentYear = (Get-Date).Year
    $Args += @($currentYear - 1, $currentYear)
}

if ($DryRun) { $Args += "--dry-run" }

Write-Host "=== CVM Atualizar Dados — $(Get-Date) ===" -ForegroundColor Cyan
Write-Host "Script : $Script"
Write-Host "Args   : $($Args -join ' ')"
Write-Host "Log    : $LogFile"
Write-Host ""

& $Venv $Script @Args 2>&1 | Tee-Object -FilePath $LogFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Atualização concluída com sucesso." -ForegroundColor Green
} else {
    Write-Host "`n❌ Erro na atualização (exit code $LASTEXITCODE). Verifique $LogFile" -ForegroundColor Red
}
