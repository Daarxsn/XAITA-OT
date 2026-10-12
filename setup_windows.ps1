$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Find-Python312 {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $v = (& $py.Source -3.12 --version 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $v -match '^Python 3\.12\.') {
                return @{ exe = $py.Source; prefix = @('-3.12') }
            }
        } catch {}
    }
    $p = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (Test-Path $p) {
        $v = (& $p --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $v -match '^Python 3\.12\.') {
            return @{ exe = $p; prefix = @() }
        }
    }
    return $null
}

Write-Host "XAITA-OT first-time setup" -ForegroundColor Cyan
Write-Host "This needs internet access and may take several minutes."
$py312 = Find-Python312
if (-not $py312) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "Python 3.12 and winget were not found." -ForegroundColor Yellow
        Write-Host "Install 64-bit Python 3.12 from https://www.python.org/downloads/windows/."
        Write-Host "Enable the Python Launcher. Then reopen this folder and rerun SETUP_WINDOWS.cmd."
        exit 2
    }
    Write-Host "Installing Python 3.12 for this user..." -ForegroundColor Yellow
    & $winget.Source install --exact --id Python.Python.3.12 --source winget --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Automatic install failed. Install Python from https://www.python.org/downloads/windows/ then rerun SETUP_WINDOWS.cmd." -ForegroundColor Red
        exit 2
    }
    $py312 = Find-Python312
}
if (-not $py312) {
    Write-Host "Python is installed but not visible yet. Close this window and rerun SETUP_WINDOWS.cmd." -ForegroundColor Yellow
    exit 2
}

$venv = Join-Path $Root ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $args = @()
    $args += $py312.prefix
    $args += @("-m", "venv", $venv)
    & $py312.exe @args
    if ($LASTEXITCODE -ne 0) { throw "Unable to create the Python virtual environment." }
}

$logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$installLog = Join-Path $logs "setup-install.log"
Write-Host "Installing dependencies; logs are saved to logs\setup-install.log."
& $venvPython -m pip install --upgrade pip setuptools wheel 2>&1 | Tee-Object -FilePath $installLog
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed. Check logs\setup-install.log and internet access." }
& $venvPython -m pip install -e . 2>&1 | Tee-Object -FilePath $installLog -Append
if ($LASTEXITCODE -ne 0) { throw "Project dependency install failed. Check logs\setup-install.log and free disk space, then rerun setup." }

$outDir = Join-Path $Root "artifacts\first_run"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
& $venvPython -m xaita_ot.cli synthetic-data --rows 128 --out (Join-Path $outDir "synthetic_smoke.csv")
if ($LASTEXITCODE -ne 0) { throw "Synthetic data smoke test failed." }
& $venvPython -m xaita_ot.cli demo --out (Join-Path $outDir "demo_smoke.json")
if ($LASTEXITCODE -ne 0) { throw "Demo smoke test failed." }
& $venvPython -c "from xaita_ot.api.app import app; print('Dashboard API import: OK')"
if ($LASTEXITCODE -ne 0) { throw "Dashboard API import failed." }

Write-Host "SETUP COMPLETE. Double-click RUN_DASHBOARD.cmd to open the dashboard." -ForegroundColor Green
Write-Host "No Git installation is required. Real benchmark data is supplied separately."
