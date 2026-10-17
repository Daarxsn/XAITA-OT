$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$py = Join-Path $Root ".venv\Scripts\python.exe"
$url = "http://127.0.0.1:8080"
$healthUrl = "http://127.0.0.1:8080/health"

if (-not (Test-Path $py)) {
    Write-Host "Run SETUP_WINDOWS.cmd first." -ForegroundColor Yellow
    exit 2
}
try {
    $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($health.StatusCode -eq 200) {
        Start-Process "$url/"
        Write-Host "XAITA-OT was already running; opened the dashboard."
        exit 0
    }
} catch {}

$logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$stdout = Join-Path $logs "dashboard-stdout.log"
$stderr = Join-Path $logs "dashboard-stderr.log"
$server = Start-Process -FilePath $py -ArgumentList @("run_api.py") -WorkingDirectory $Root -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
try {
    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        $server.Refresh()
        if ($server.HasExited) { break }
        try {
            $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) {
        Write-Host "Dashboard failed to start. Recent logs:" -ForegroundColor Red
        if (Test-Path $stderr) { Get-Content $stderr -Tail 40 }
        if (Test-Path $stdout) { Get-Content $stdout -Tail 40 }
        throw "See logs\dashboard-stderr.log and logs\dashboard-stdout.log."
    }
    Start-Process "$url/"
    Write-Host "Dashboard: $url/" -ForegroundColor Green
    Write-Host "API docs: $url/docs"
    Write-Host "Keep this window open. Press Ctrl+C to stop."
    while ($true) {
        $server.Refresh()
        if ($server.HasExited) { break }
        Start-Sleep -Seconds 1
    }
} finally {
    $server.Refresh()
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
}
