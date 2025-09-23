Param(
  [ValidateSet('start','bootstrap','pull-models')]
  [string]$Command = 'start'
)

$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot 'backend'
$devpy = Join-Path $backend 'dev.py'

if (-not (Test-Path $devpy)) {
  Write-Error "dev.py not found at $devpy"
  exit 1
}

$py = $null
try { $py = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $py) {
  try { $py = (Get-Command py -ErrorAction Stop).Source } catch {}
}
if (-not $py) {
  Write-Error 'Python not found in PATH. Install Python 3.10+.'
  exit 1
}

& $py $devpy $Command

