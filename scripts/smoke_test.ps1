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

function Test-Endpoint {
    param(
        [string]$Url,
        [int]$ExpectedStatusCode = 200
    )

    Write-Info "Checking $Url"

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
    }
    catch {
        throw "Endpoint check failed: $Url"
    }

    if ($response.StatusCode -ne $ExpectedStatusCode) {
        throw "Unexpected status code for $Url. Expected $ExpectedStatusCode, got $($response.StatusCode)"
    }

    Write-Ok "$Url returned $ExpectedStatusCode"
}

try {
    Test-Endpoint "http://127.0.0.1:8000/api/v1/health"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/metrics"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/metrics/prometheus"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/rag/status"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/llm/status"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/admin/db/status"
    Test-Endpoint "http://127.0.0.1:8000/api/v1/admin/storage/privacy-check"
    Test-Endpoint "http://127.0.0.1:8000/web/"
    Test-Endpoint "http://127.0.0.1:9090/-/ready"
    Test-Endpoint "http://127.0.0.1:3000/api/health"
    Test-Endpoint "http://127.0.0.1:5050"

    Write-Host ""
    Write-Ok "Smoke test completed successfully."
}
catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}