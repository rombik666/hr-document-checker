Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Warning!" -ForegroundColor Yellow
Write-Host "This script will stop containers and remove Docker volumes." -ForegroundColor Yellow
Write-Host "PostgreSQL, Prometheus and Grafana Docker volumes will be removed." -ForegroundColor Yellow
Write-Host "Local data/ and backups/ directories will NOT be removed." -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Type YES to continue"

if ($confirmation -ne "YES") {
    Write-Host "Reset cancelled." -ForegroundColor Cyan
    exit 0
}

try {
    docker compose down -v --remove-orphans

    if ($LASTEXITCODE -ne 0) {
        throw "docker compose down -v failed."
    }

    Write-Host "[OK] Docker environment has been reset." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}