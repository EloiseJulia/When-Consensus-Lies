$maxAttempts = 20
$attempt = 1
$repo = "C:\Users\v-elzhang\Desktop\MyFolder\When Consensus Lies"
$logFile = "$repo\watcher_loop.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log "=== WATCHER RETRY LOOP START (max $maxAttempts attempts) ==="

while ($attempt -le $maxAttempts) {
    Log "--- Attempt $attempt / $maxAttempts ---"
    
    # Set env
    $env:GITHUB_MODELS_TOKEN = [Environment]::GetEnvironmentVariable('GITHUB_MODELS_TOKEN','User')
    $env:RUN_DEFAULT_CHECK = '1'
    
    if ([string]::IsNullOrEmpty($env:GITHUB_MODELS_TOKEN)) {
        Log "ERROR: GITHUB_MODELS_TOKEN is empty — STOPPING"
        break
    }
    
    # Run driver
    Set-Location $repo
    $runOut = python scripts/default_check.py 2>&1 | Out-String
    Log "Driver output (last 500 chars): $($runOut[-500..-1] -join '')"
    
    # Check for data_typical_001 reasoner row in summary
    $summaryPath = "$repo\default_check_summary.jsonl"
    $hasReasonerRow = $false
    if (Test-Path $summaryPath) {
        $rows = Get-Content $summaryPath | ForEach-Object {
            try { $_ | ConvertFrom-Json } catch {}
        } | Where-Object { $_ -ne $null }
        $target = $rows | Where-Object {
            $_.task_id -like "data_typical_001*" -and $_.model_class -eq "reasoner"
        }
        if ($target) {
            $hasReasonerRow = $true
            Log "SUCCESS: Found data_typical_001 reasoner row(s)!"
        }
    }
    
    if ($hasReasonerRow) {
        Log "=== ESSENTIAL REASONER ARM COMPLETE — BREAKING LOOP ==="
        break
    }
    
    $attempt++
    if ($attempt -le $maxAttempts) {
        Log "Still capped. Sleeping 3600s before attempt $attempt..."
        Start-Sleep -Seconds 3600
    }
}

if ($attempt -gt $maxAttempts) {
    Log "=== MAX ATTEMPTS REACHED — still capped after ~20h. INCOMPLETE. ==="
}

Log "=== WATCHER LOOP END ==="
