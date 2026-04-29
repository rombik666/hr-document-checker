param(
    [switch]$NoBuild,
    [switch]$Logs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-DockerInstalled {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue

    if (-not $dockerCommand) {
        throw "Docker was not found. Install Docker Desktop and try again."
    }
}

function Test-DockerRunning {
    docker info *> $null

    if ($LASTEXITCODE -ne 0) {
        throw "Docker is installed, but Docker Desktop is not running."
    }
}

function Ensure-EnvFile {
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Ok "Created .env from .env.example"
        }
        else {
            Write-Warn ".env.example was not found. Skipping .env creation."
        }
    }
    else {
        Write-Info ".env already exists"
    }
}

function Ensure-ProjectDirectories {
    $directories = @(
        "data",
        "data\samples",
        "data\knowledge_base",
        "data\index",
        "backups",
        "logs"
    )

    foreach ($directory in $directories) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
            Write-Ok "Created directory: $directory"
        }
    }
}

function Try-CreateDemoSamples {
    if (-not (Test-Path "scripts\create_demo_samples.py")) {
        Write-Warn "scripts\create_demo_samples.py was not found. Demo samples were not created."
        return
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue

    if (-not $pythonCommand) {
        Write-Warn "Local Python was not found. Demo samples were not created."
        return
    }

    try {
        python scripts\create_demo_samples.py
        Write-Ok "Demo samples prepared"
    }
    catch {
        Write-Warn "Failed to create demo samples. Docker startup can continue."
    }
}

function Start-DockerCompose {
    $composeArgs = @("up", "-d")

    if (-not $NoBuild) {
        $composeArgs += "--build"
    }

    Write-Info "Running: docker compose $($composeArgs -join ' ')"

    docker compose @composeArgs

    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed."
    }

    Write-Ok "Docker containers started"
}

function Show-Links {
    Write-Host ""
    Write-Host "System is running." -ForegroundColor Green
    Write-Host ""
    Write-Host "Web UI:             http://127.0.0.1:8000/web/" -ForegroundColor White
    Write-Host "Swagger API:        http://127.0.0.1:8000/docs" -ForegroundColor White
    Write-Host "Health check:       http://127.0.0.1:8000/api/v1/health" -ForegroundColor White
    Write-Host "JSON metrics:       http://127.0.0.1:8000/api/v1/metrics" -ForegroundColor White
    Write-Host "RAG status:         http://127.0.0.1:8000/api/v1/rag/status" -ForegroundColor White
    Write-Host "Prometheus:         http://127.0.0.1:9090" -ForegroundColor White
    Write-Host "Grafana:            http://127.0.0.1:3000" -ForegroundColor White
    Write-Host "pgAdmin:            http://127.0.0.1:5050" -ForegroundColor White
    Write-Host ""
    Write-Host "Grafana login:      admin" -ForegroundColor White
    Write-Host "Grafana password:   admin" -ForegroundColor White
    Write-Host "pgAdmin email:      admin@example.com" -ForegroundColor White
    Write-Host "pgAdmin password:   admin" -ForegroundColor White
    Write-Host ""
    Write-Host "Stop system:        .\stop.ps1" -ForegroundColor Yellow
    Write-Host "Reset environment:  .\reset.ps1" -ForegroundColor Yellow
    Write-Host ""
}

try {
    Write-Info "Checking Docker"
    Test-DockerInstalled
    Test-DockerRunning
    Write-Ok "Docker is available"

    Ensure-EnvFile
    Ensure-ProjectDirectories
    Try-CreateDemoSamples
    Start-DockerCompose
    Show-Links

    if ($Logs) {
        Write-Info "Showing app logs. Press Ctrl+C to exit logs."
        docker compose logs -f app
    }
}
catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}