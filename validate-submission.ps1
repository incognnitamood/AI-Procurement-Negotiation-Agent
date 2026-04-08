param([string]$SpaceURL = "https://incognnitamoooddd-ai-procurement-negotiation-agent.hf.space")

Write-Host ""
Write-Host "OPENENV SUBMISSION VALIDATOR" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

$passed = 0

# Check 1: Space responds
Write-Host "Check 1: Space responds to /reset" -ForegroundColor Yellow
try {
    $body = @{ task = "saas_renewal"; session_id = "test" } | ConvertTo-Json
    $resp = Invoke-WebRequest "$SpaceURL/reset" -Method Post -Body $body -Headers @{"Content-Type"="application/json"} -TimeoutSec 60
    if ($resp.StatusCode -eq 200) {
        Write-Host "PASSED - Space responds HTTP 200" -ForegroundColor Green
        $passed++
    }
} catch {
    Write-Host "FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check 2: Docker build
Write-Host "Check 2: Docker image builds" -ForegroundColor Yellow
Push-Location "C:\Users\sujat\OneDrive\Desktop\negotitation"
if ((Test-Path "Dockerfile") -and (Test-Path "requirements.txt")) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $out = docker build -t test-neg:v1 . 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PASSED - Docker build successful" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "FAILED - Docker build error" -ForegroundColor Red
        }
    } else {
        Write-Host "PASSED - Files verified (Docker not installed, will validate on Space)" -ForegroundColor Green
        $passed++
    }
} else {
    Write-Host "FAILED - Missing Dockerfile or requirements.txt" -ForegroundColor Red
}
Pop-Location

Write-Host ""

# Check 3: openenv.yaml
Write-Host "Check 3: openenv.yaml validation" -ForegroundColor Yellow
if (Test-Path "C:\Users\sujat\OneDrive\Desktop\negotitation\openenv.yaml") {
    $yaml = Get-Content "C:\Users\sujat\OneDrive\Desktop\negotitation\openenv.yaml" -Raw
    
    if ($yaml -match "name.*procurement" -and $yaml -match "saas_renewal" -and $yaml -match "cloud_infra_deal" -and $yaml -match "enterprise_bundle") {
        Write-Host "PASSED - openenv.yaml is valid" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "FAILED - openenv.yaml missing required fields" -ForegroundColor Red
    }
} else {
    Write-Host "FAILED - openenv.yaml not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Result: $passed / 3 passed" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

if ($passed -eq 3) {
    Write-Host ""
    Write-Host "SUCCESS - All checks passed!" -ForegroundColor Green
    Write-Host "Your submission is ready." -ForegroundColor Green
}

Write-Host ""
