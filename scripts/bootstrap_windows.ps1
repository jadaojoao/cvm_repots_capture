param(
    [switch]$ForceRecreateVenv,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-CommandArray {
    param(
        [string[]]$BaseCommand,
        [string[]]$ExtraArgs = @()
    )
    $exe = $BaseCommand[0]
    $baseArgs = @()
    if ($BaseCommand.Count -gt 1) {
        $baseArgs = $BaseCommand[1..($BaseCommand.Count - 1)]
    }
    & $exe @baseArgs @ExtraArgs | Out-Host
    return [int]$LASTEXITCODE
}

function Test-PythonCommand {
    param([string[]]$Command)
    try {
        $code = Invoke-CommandArray -BaseCommand $Command -ExtraArgs @("-c", "import sys")
        return $code -eq 0
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    $pythonExeFromUserInstall = "$env:LocalAppData\Programs\Python\Python311\python.exe"
    if (Test-Path $pythonExeFromUserInstall) {
        return @($pythonExeFromUserInstall)
    }

    $candidates = @(
        @("python"),
        @("py", "-3.11"),
        @("py", "-3"),
        @("py")
    )

    foreach ($cmd in $candidates) {
        if (Test-PythonCommand -Command $cmd) {
            return @($cmd)
        }
    }

    return @()
}

function Install-PythonWithWinget {
    Write-Step "Python nao encontrado. Tentando instalar via winget (Python 3.11)."
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    $wingetExe = $null
    if ($wingetCmd) {
        $wingetExe = $wingetCmd.Source
    } else {
        $wingetFallback = "$env:LocalAppData\Microsoft\WindowsApps\winget.exe"
        if (Test-Path $wingetFallback) {
            $wingetExe = $wingetFallback
        }
    }

    if (-not $wingetExe) {
        throw "winget nao esta disponivel neste Windows. Instale Python manualmente e rode o bootstrap novamente."
    }

    & $wingetExe install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na instalacao do Python via winget."
    }

    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath;$env:Path"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirementsFile = Join-Path $repoRoot "requirements.txt"

Write-Step "Detectando Python no sistema"
$pythonCmd = @(Resolve-PythonCommand)
if ($pythonCmd.Count -eq 0) {
    Install-PythonWithWinget
    $pythonCmd = @(Resolve-PythonCommand)
    if ($pythonCmd.Count -eq 0) {
        throw "Python ainda nao encontrado apos tentativa de instalacao."
    }
}

$versionCode = Invoke-CommandArray -BaseCommand $pythonCmd -ExtraArgs @("--version")
if ($versionCode -ne 0) {
    throw "Falha ao consultar versao do Python."
}

if ((Test-Path $venvDir) -and $ForceRecreateVenv) {
    Write-Step "Removendo ambiente virtual existente (.venv)"
    Remove-Item -Path $venvDir -Recurse -Force
}

if (-not (Test-Path $venvPython)) {
    Write-Step "Criando ambiente virtual em .venv"
    $venvCode = Invoke-CommandArray -BaseCommand $pythonCmd -ExtraArgs @("-m", "venv", $venvDir)
    if ($venvCode -ne 0) {
        throw "Falha ao criar ambiente virtual."
    }
}

Write-Step "Atualizando pip/setuptools/wheel"
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao atualizar pip/setuptools/wheel."
}

Write-Step "Instalando dependencias de requirements.txt"
& $venvPython -m pip install -r $requirementsFile
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar dependencias do requirements.txt."
}

$smokeScript = Join-Path $repoRoot "scripts\smoke_validate.py"
$doctorScript = Join-Path $repoRoot "scripts\runtime_doctor.py"
if ((Test-Path $smokeScript) -and (-not $SkipSmoke)) {
    Write-Step "Rodando smoke validate (modo rapido --skip-compile)"
    & $venvPython $smokeScript --skip-compile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Aviso: smoke_validate retornou erro. Revise os arquivos de dados esperados." -ForegroundColor Yellow
    }
}

if (Test-Path $doctorScript) {
    Write-Step "Rodando runtime_doctor para validar ambiente basico"
    & $venvPython $doctorScript --require-canonical
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Aviso: runtime_doctor encontrou problemas. Revise a configuracao antes de rodar o app." -ForegroundColor Yellow
    }
}

Write-Step "Bootstrap concluido"
Write-Host "Ative o ambiente virtual com:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Exemplo de execucao do scraper:"
Write-Host "  python main.py --companies PETROBRAS --start_year 2021 --end_year 2025 --type consolidated"
