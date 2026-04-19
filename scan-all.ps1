<#
.SYNOPSIS
    Scans every project listed in targets.txt and writes one HTML report per project.
.DESCRIPTION
    Reads targets.txt (one absolute path per line, # for comments).
    For each path, sets TARGET_PATH and runs docker-compose, saving the report to
    ./reports/<project-name>/report.html on the host.
#>

$ErrorActionPreference = "Stop"

$scriptDir  = $PSScriptRoot
$targetsFile = Join-Path $scriptDir "targets.txt"
$reportsBase = Join-Path $scriptDir "reports"

if (-not (Test-Path $targetsFile)) {
    Write-Error "targets.txt not found at $targetsFile"
    exit 1
}

$targets = Get-Content $targetsFile |
    Where-Object { $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*$' } |
    ForEach-Object { $_.Trim() }

if ($targets.Count -eq 0) {
    Write-Warning "No targets found in targets.txt."
    exit 0
}

$failedTargets = @()

foreach ($target in $targets) {
    if (-not (Test-Path $target)) {
        Write-Warning "Skipping (path not found): $target"
        $failedTargets += $target
        continue
    }

    $projectName = Split-Path $target -Leaf
    $reportDir   = Join-Path $reportsBase $projectName
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Scanning: $target" -ForegroundColor Cyan
    Write-Host "  Report  : $reportDir\report.html" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

    $env:TARGET_PATH  = $target
    $env:REPORTS_PATH = $reportDir

    Push-Location $scriptDir
    try {
        docker-compose run --rm auditor
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "docker-compose exited with code $LASTEXITCODE for: $target"
            $failedTargets += $target
        }
    } finally {
        Pop-Location
        Remove-Item Env:\TARGET_PATH  -ErrorAction SilentlyContinue
        Remove-Item Env:\REPORTS_PATH -ErrorAction SilentlyContinue
    }
}

Write-Host ""
if ($failedTargets.Count -gt 0) {
    Write-Host "Finished with errors for:" -ForegroundColor Yellow
    $failedTargets | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    exit 1
} else {
    Write-Host "All scans completed successfully." -ForegroundColor Green
}
