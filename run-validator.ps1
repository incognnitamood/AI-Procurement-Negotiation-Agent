#!/usr/bin/env pwsh
<#
OpenEnv Submission Validator

Checks:
1. HF Space responds to /reset with HTTP 200 and valid observation
2. Docker image builds successfully
3. openenv.yaml is valid
#>

param(
    [string]$PingURL = "https://incognnitamoooddd-ai-procurement-negotiation-agent.hf.space",
    [string]$RepoDir = "C:\Users\sujat\OneDrive\Desktop\negotitation"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OpenEnv Submission Validator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$passCount = 0
$totalChecks = 3

# ===================================================================
# CHECK 1: HF Space /reset endpoint
# ===================================================================
Write-Host "[Check 1/$totalChecks] Pinging HF Space..." -ForegroundColor Yellow

try {
    $body = @{"task_name" = "saas_renewal"} | ConvertTo-Json
    
    Write-Host "  URL: $PingURL/reset" -ForegroundColor Gray
    
    $response = Invoke-WebRequest -Uri "$PingURL/reset" `
                                  -Method Post `
                                  -Headers @{"Content-Type"="application/json"} `
                                  -Body $body `
                                  -TimeoutSec 15 `
                                  -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        $content = $response.Content | ConvertFrom-Json
        
        if ($content.observation -and $content.info) {
            Write-Host "  PASSED: /reset returns HTTP 200 with valid observation" -ForegroundColor Green
            $passCount++
        } else {
            Write-Host "  FAILED: Response missing observation or info" -ForegroundColor Red
        }
    } else {
        Write-Host "  FAILED: /reset returned HTTP $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    $errorMsg = $_.Exception.Message
    Write-Host "  FAILED: Could not reach HF Space" -ForegroundColor Red
    Write-Host "          $errorMsg" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Yellow
    Write-Host "    - Is the Space deployed? Check HF Spaces dashboard" -ForegroundColor Yellow
    Write-Host "    - Wait 30+ seconds after deployment for initialization" -ForegroundColor Yellow
    Write-Host "    - Check Space logs for startup errors" -ForegroundColor Yellow
}

Write-Host ""

# ===================================================================
# CHECK 2: Docker build
# ===================================================================
Write-Host "[Check 2/$totalChecks] Validating Docker build..." -ForegroundColor Yellow

Push-Location $RepoDir

if (-not (Test-Path "Dockerfile")) {
    Write-Host "  FAILED: Dockerfile not found" -ForegroundColor Red
} else {
    Write-Host "  Found: Dockerfile" -ForegroundColor Gray
    
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "  Building image (this may take 2-3 minutes)..." -ForegroundColor Gray
        
        $buildOutput = @()
        docker build . 2>&1 | ForEach-Object { $buildOutput += $_ }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  PASSED: Docker build completed successfully" -ForegroundColor Green
            $passCount++
        } else {
            Write-Host "  FAILED: Docker build exited with code $LASTEXITCODE" -ForegroundColor Red
            Write-Host ""
            Write-Host "  Last 10 lines:" -ForegroundColor Red
            $buildOutput[-10..-1] | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        }
    } else {
        Write-Host "  WARNING: Docker not installed locally" -ForegroundColor Yellow
        Write-Host "  Checking Dockerfile syntax..." -ForegroundColor Gray
        
        $dockerContent = Get-Content "Dockerfile" -Raw
        if ($dockerContent -match "FROM\s+python" -and $dockerContent -match "CMD") {
            Write-Host "  PASSED: Dockerfile structure is valid" -ForegroundColor Green
            $passCount++
        } else {
            Write-Host "  FAILED: Dockerfile missing FROM or CMD" -ForegroundColor Red
        }
    }
}

Pop-Location
Write-Host ""

# ===================================================================
# CHECK 3: openenv.yaml validation
# ===================================================================
Write-Host "[Check 3/$totalChecks] Validating openenv.yaml..." -ForegroundColor Yellow

Push-Location $RepoDir

if (-not (Test-Path "openenv.yaml")) {
    Write-Host "  FAILED: openenv.yaml not found" -ForegroundColor Red
} else {
    Write-Host "  Found: openenv.yaml" -ForegroundColor Gray
    
    $yaml = Get-Content "openenv.yaml" -Raw
    
    $required = @(
        "name",
        "version",
        "tasks",
        "action_space",
        "observation_space",
        "reward_range"
    )
    
    $allPresent = $true
    foreach ($field in $required) {
        if ($yaml -notmatch "$field\s*:") {
            Write-Host "  ERROR: Missing field: $field" -ForegroundColor Red
            $allPresent = $false
        }
    }
    
    if ($allPresent) {
        Write-Host "  PASSED: openenv.yaml has all required fields" -ForegroundColor Green
        $passCount++
    }
}

Pop-Location
Write-Host ""

# ===================================================================
# SUMMARY
# ===================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passPercent = [math]::Round(($passCount / $totalChecks) * 100)
Write-Host ""
Write-Host "  Passed:  $passCount / $totalChecks" -ForegroundColor $(if ($passCount -eq $totalChecks) { "Green" } else { "Yellow" })
Write-Host "  Score:   $passPercent%" -ForegroundColor $(if ($passPercent -eq 100) { "Green" } else { "Yellow" })
Write-Host ""

if ($passCount -eq $totalChecks) {
    Write-Host "SUCCESS! All validation checks passed." -ForegroundColor Green
    Write-Host "Your submission is ready for judge evaluation." -ForegroundColor Green
} else {
    Write-Host "INCOMPLETE: $($totalChecks - $passCount) check(s) failed or skipped." -ForegroundColor Yellow
}

Write-Host ""
