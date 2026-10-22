# PLAN-10 clean-env helper (read-only checks + printed steps).
# Does NOT copy .env, does NOT drop databases, does NOT call cloud APIs.
# Run from repository root in PowerShell.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== PLAN-10 clean-env checklist (print-only where destructive) ==="
Write-Host "Repo:" (Get-Location).Path
Write-Host "Git HEAD:" (git rev-parse --short HEAD)
Write-Host "Python:" (& backend\.venv\Scripts\python.exe -c "import sys; print(sys.version.split()[0])" 2>$null)
Write-Host "Node:" (node -v)
Write-Host "Alembic head:" (& backend\.venv\Scripts\python.exe -c "from alembic.script import ScriptDirectory; print(ScriptDirectory('backend/alembic').get_current_head())")

Write-Host ""
Write-Host "Required files:"
@(
  ".env.example", "LICENSE", "NOTICE", "docker-compose.yml",
  "backend/pyproject.toml", "frontend/package-lock.json",
  "docs/workflow.md", "docs/final-delivery-checklist.md"
) | ForEach-Object {
  if (Test-Path $_) { Write-Host "  OK  $_" } else { Write-Host "  MISSING $_" }
}

Write-Host ""
Write-Host "Gate commands (run explicitly; this script does not execute them):"
Write-Host '  backend/.venv/Scripts/python.exe -m pytest backend/tests -q'
Write-Host '  backend/.venv/Scripts/python.exe -m ruff check backend'
Write-Host '  cd frontend; npm run build'
Write-Host ""
Write-Host "Blank-machine install / isolated pg_dump restore: see docs/final-delivery-checklist.md section 2"
Write-Host "Do not claim PASS for independent trial or clean-env drill from this helper alone."
