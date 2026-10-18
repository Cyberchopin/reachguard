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
$taskProbe = 'import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ("pytest","fastapi","httpx","networkx","cryptography","onnxruntime","pipecat")) else 1)'
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
    Write-Host 'No complete test environment found. See START_HERE.md; no packages were installed.'
    exit 1
}
Write-Host 'Running offline checks. No microphone or API key is needed.'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskSelected -m scripts.check_local
    $taskExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
Write-Host "Report: $(Join-Path $PSScriptRoot 'scambench/LOCAL_RESULTS.md')"
exit $taskExitCode
