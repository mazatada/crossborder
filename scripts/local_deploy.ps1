param(
    [string]$RepoPath = "D:\\works2025\\越境EC\\crossover_win\\crossborder",
    [string]$ComposeDir = "D:\\works2025\\越境EC\\crossover_win\\crossborder",
    [string]$Branch = "main",
    [string]$GitRemote = "origin",
    [string]$ServiceUrl = "http://localhost:65001",
    [int]$MaxAttempts = 10,
    [int]$SleepSeconds = 15,
    [switch]$Build,
    [string]$LastGoodFile = "D:\\works2025\\越境EC\\crossover_win\\crossborder\\.last_good_commit",
    [string]$LockFile = "D:\\works2025\\越境EC\\crossover_win\\crossborder\\.deploy_lock"
)

$ErrorActionPreference = "Stop"
$startDir = Get-Location

function Write-Log {
    param([string]$Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Output "[$ts] $Message"
}

function Test-Health {
    $healthUrl = "$ServiceUrl/v1/health"
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) {
                Write-Log "Health check OK: $healthUrl"
                return $true
            }
        } catch {
            Write-Log "Health check failed (attempt $i/$MaxAttempts): $($_.Exception.Message)"
        }
        Start-Sleep -Seconds $SleepSeconds
    }
    return $false
}

Write-Log "Starting local deploy check (branch=$Branch)"

if (Test-Path $LockFile) {
    Write-Log "Lock file exists, exiting: $LockFile"
    exit 0
}
New-Item -Path $LockFile -ItemType File -Force | Out-Null

try {
Push-Location $RepoPath
git checkout $Branch | Out-Null
git remote get-url $GitRemote | Out-Null
git fetch $GitRemote $Branch | Out-Null
$local = (git rev-parse $Branch).Trim()
$remote = (git rev-parse "$GitRemote/$Branch").Trim()

if ($local -ne $remote) {
    Write-Log "Update detected: $local -> $remote"
    git pull --ff-only
    Pop-Location

    Push-Location $ComposeDir
    if ($Build.IsPresent) {
        Write-Log "Building images"
        docker compose build
    }
    Write-Log "Applying compose changes"
    docker compose up -d
    Pop-Location

    if (-not (Test-Health)) {
        Write-Log "Health check failed after update."
        if (Test-Path $LastGoodFile) {
            $lastGood = (Get-Content -Path $LastGoodFile -ErrorAction SilentlyContinue).Trim()
            if ($lastGood) {
                Write-Log "Rolling back to last good commit: $lastGood"
                Push-Location $RepoPath
                git checkout $lastGood
                Pop-Location
                Push-Location $ComposeDir
                docker compose up -d
                Pop-Location
                if (-not (Test-Health)) {
                    throw "Rollback health check failed."
                }
                Write-Log "Rollback succeeded"
                return
            }
        }
        throw "Health check failed and no rollback target found."
    }
    Set-Content -Path $LastGoodFile -Value $remote
    Write-Log "Deploy succeeded"
} else {
    Write-Log "No update. Skipping deploy."
    Pop-Location
}
} finally {
    if (Test-Path $LockFile) {
        Remove-Item -Path $LockFile -Force
    }
    Set-Location $startDir
}
