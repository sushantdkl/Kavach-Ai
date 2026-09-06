$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
