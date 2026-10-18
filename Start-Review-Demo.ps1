param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$taskCandidates = @()
if ($PythonPath) {
    $taskCandidates += $PythonPath
} else {
    $taskCandidates += (Join-Path $PSScriptRoot '.venv-integrations/Scripts/python.exe')
    $taskCandidates += (Join-Path $env:USERPROFILE 'Documents/Codex/work/cg-int/Scripts/python.exe')
    $taskCandidates += (Join-Path $PSScriptRoot '.venv/Scripts/python.exe')
    $taskPythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($taskPythonCommand) { $taskCandidates += $taskPythonCommand.Source }
}
$taskSelected = $null
$taskProbe = 'import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ("fastapi","uvicorn","cryptography")) else 1)'
foreach ($taskCandidate in $taskCandidates) {
    if (Test-Path -LiteralPath $taskCandidate -PathType Leaf) {
        $taskProbeExitCode = 1
        try {
            & $taskCandidate -c $taskProbe 2>$null
            $taskProbeExitCode = $LASTEXITCODE
        } catch {
            # A broken candidate is expected; continue to the next environment.
            $taskProbeExitCode = 1
        }
        if ($taskProbeExitCode -eq 0) { $taskSelected = $taskCandidate; break }
    }
}
if (-not $taskSelected) {
    Write-Host 'Review demo dependencies missing. See START_HERE.md. Nothing was installed.'
    exit 1
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskSelected -m scripts.start_review_demo
    $taskExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExitCode
