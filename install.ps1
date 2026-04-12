# CivicRecords AI — Windows Installation Script
# Requires: Windows 10/11 with Docker Desktop

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CivicRecords AI - Installation Script"
Write-Host "  Target: Windows 10/11 with Docker Desktop"
Write-Host "============================================"
Write-Host ""

# Check Docker
try {
    $dockerVersion = docker --version 2>$null
    Write-Host "[OK] Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not installed or not running." -ForegroundColor Red
    Write-Host "Install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    Write-Host "After installing, make sure Docker Desktop is running before re-running this script."
    exit 1
}

# Check Docker Compose
try {
    $composeVersion = docker compose version 2>$null
    Write-Host "[OK] Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Compose not available." -ForegroundColor Red
    exit 1
}

# Check Docker is actually running
try {
    docker info 2>$null | Out-Null
    Write-Host "[OK] Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker daemon is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Create .env from template if not exists
if (-not (Test-Path ".env")) {
    Write-Host ">>> Creating .env from template..."
    Copy-Item ".env.example" ".env"
    # Generate JWT secret
    $jwtSecret = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
    (Get-Content ".env") -replace "CHANGE-ME-generate-with-openssl-rand-hex-32", $jwtSecret | Set-Content ".env"
    Write-Host ""
    Write-Host "IMPORTANT: Edit .env to set your admin email and password:" -ForegroundColor Yellow
    Write-Host "  notepad .env"
    Write-Host ""
    Read-Host "Press Enter after editing .env, or Ctrl+C to edit later"
}

# Pull and start services
Write-Host ">>> Pulling Docker images..."
docker compose pull

Write-Host ">>> Building application images..."
docker compose build

Write-Host ">>> Running database migrations..."
docker compose up -d postgres redis
Start-Sleep -Seconds 10
docker compose run --rm api alembic upgrade head

Write-Host ">>> Starting all services..."
docker compose up -d

# Wait for health
Write-Host ">>> Waiting for services to be healthy..."
$healthy = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "ok") {
            Write-Host "API is healthy!" -ForegroundColor Green
            $healthy = $true
            break
        }
    } catch {}
    Write-Host "  Waiting... ($i/30)"
    Start-Sleep -Seconds 5
}

if (-not $healthy) {
    Write-Host "[WARN] API health check timed out. Check logs with: docker compose logs api" -ForegroundColor Yellow
}

# Pull embedding model
Write-Host ">>> Pulling embedding model (required for search)..."
docker compose exec ollama ollama pull nomic-embed-text

Write-Host ""
Write-Host ">>> To enable AI-powered search, pull a language model:"
Write-Host "    docker compose exec ollama ollama pull gemma4:26b    (recommended, ~15GB)"
Write-Host "    docker compose exec ollama ollama pull gemma3:4b     (lighter alternative, ~2.5GB)"

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" } | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installation complete!"
Write-Host ""
Write-Host "  Admin panel:  http://${ip}:8080"
Write-Host "  API:          http://${ip}:8000"
Write-Host "  API docs:     http://${ip}:8000/docs"
Write-Host ""
Write-Host "  Run sovereignty check: .\scripts\verify-sovereignty.ps1"
Write-Host "============================================" -ForegroundColor Cyan
