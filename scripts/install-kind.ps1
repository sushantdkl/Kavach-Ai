$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .tools | Out-Null
$KavachRelease = 'https://kind.sigs.k8s.io/dl/v0.33.0'
Invoke-WebRequest "$KavachRelease/kind-windows-amd64" -OutFile .tools/kind.exe
Invoke-WebRequest "$KavachRelease/kind-windows-amd64.sha256sum" -OutFile .tools/kind.sha256sum
$KavachExpected = ((Get-Content .tools/kind.sha256sum) -split '\s+')[0]
$KavachActual = (Get-FileHash .tools/kind.exe -Algorithm SHA256).Hash
if ($KavachExpected -ne $KavachActual) { throw 'kind release checksum mismatch; do not execute' }
./.tools/kind.exe version
if ($LASTEXITCODE -ne 0) { throw 'kind version check failed' }
