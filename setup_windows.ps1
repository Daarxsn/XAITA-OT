$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @(
        $machinePath,
        $userPath,
        "$env:LOCALAPPDATA\Programs\Python\Launcher",
        "$env:LOCALAPPDATA\Programs\Python\Python312",
        "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
    )
    $env:Path = ($parts | Where-Object { $_ -and $_.Trim() } | Select-Object -Unique) -join ";"
}

function Get-Python312Command {
    Refresh-ProcessPath

    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            $version = (& $launcher.Source -3.12 --version 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $version -match "^Python 3\.12\.") {
                return @{ Command = $launcher.Source; Prefix = @("-3.12") }
            }
        } catch {}
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:LOCALAPPDATA\Microsoft\WindowsApps\python3.12.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            try {
                $version = (& $candidate --version 2>&1 | Out-String).Trim()
                if ($LASTEXITCODE -eq 0 -and $version -match "^Python 3\.12\.") {
                    return @{ Command = $candidate; Prefix = @() }
                }
            } catch {}
        }
    }
    return $null
}

Write-Host ""
Write-Host "XAITA-OT first-time setup" -ForegroundColor Cyan
Write-Host "Project folder: $ProjectRoot"
Write-Host "An internet connection is required. First-time installation may take several minutes."
Write-Host ""

$python = Get-Python312Command
if (-not $python) {
    $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "Python 3.12 and winget were not found." -ForegroundColor Yellow
        Write-Host "Install 64-bit Python 3.12 from https://www.python.org/downloads/windows/."
        Write-Host "During setup, enable the Python Launcher. Then run SETUP_WINDOWS.cmd again."
        exit 2
    }

    Write-Host "Python 3.12 is missing. Installing it for this Windows user using winget..." -ForegroundColor Yellow
    & $winget.Source install --exact --id Python.Python.3.12 --source winget --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Automatic Python installation failed. Install Python 3.12 from https://www.python.org/downloads/windows/ and retry." -ForegroundColor Red
        exit 2
    }

    $python = Get-Python312Command
}
if (-not $python) {
    Write-Host "Python may have installed, but this window cannot find Python 3.12 yet." -ForegroundColor Yellow
    Write-Host "Close this window, reopen SETUP_WINDOWS.cmd, and retry. If that fails, install Python 3.12 from https://www.python.org/downloads/windows/."
    exit 2
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating isolated project environment..." -ForegroundColor Cyan
    & $python.Command @($python.Prefix) -m venv (Join-Path $ProjectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

Write-Host "Installing XAITA-OT runtime and model dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "Could not update pip/build tools. Check the internet connection and retry." }

& $venvPython -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Check internet access/free disk space, then rerun SETUP_WINDOWS.cmd." }

$smokeDir = Join-Path $ProjectRoot "artifacts\first_run"
New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null

Write-Host "Checking the demo and dashboard import..." -ForegroundColor Cyan
& $venvPython -m xaita_ot.cli synthetic-data --rows 128 --out (Join-Path $smokeDir "synthetic_smoke.csv")
if ($LASTEXITCODE -ne 0) { throw "Synthetic-data smoke check failed." }

& $venvPython -m xaita_ot.cli demo --out (Join-Path $smokeDir "demo_smoke.json")
if ($LASTEXITCODE -ne 0) { throw "Demo smoke check failed." }

& $venvPython -c "from xaita_ot.api.app import app; print('Dashboard API import: OK')"
if ($LASTEXITCODE -ne 0) { throw "Dashboard API import smoke check failed." }

Write-Host ""
Write-Host "SETUP COMPLETE" -ForegroundColor Green
Write-Host "Now double-click RUN_DASHBOARD.cmd."
Write-Host "No Git installation is required. Real benchmark data is separate and is not included in the source ZIP."
