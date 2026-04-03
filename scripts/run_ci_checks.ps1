# Supply chain + unit tests (run from repo root: powershell -File scripts/run_ci_checks.ps1)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m pip install -q -r requirements-lock.txt
python -m pip install -q -r requirements-dev.txt
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Warning "Node.js not found; skipping React build. Install Node 20+ for full UI checks."
} else {
  Push-Location frontend
  npm ci
  npm run build
  npm test
  Pop-Location
}
python -m pytest
python -m pip_audit -r requirements-lock.txt
