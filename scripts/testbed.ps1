param([ValidateSet('create','build','deploy','status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$KavachConfig = Join-Path (Get-Location) 'infrastructure/kubeconfig'
$KavachKind = Join-Path (Get-Location) '.tools/kind.exe'
function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Exe $Arguments" }
}
switch ($Action) {
    'create' {
        Invoke-Checked docker @('info','--format','{{.ServerVersion}}')
        Invoke-Checked $KavachKind @('create','cluster','--name','kavach-lab','--config','infrastructure/kind.yaml','--kubeconfig',$KavachConfig,'--image','kindest/node:v1.34.0','--wait','180s')
    }
    'build' {
        Invoke-Checked docker @('build','-f','payment-api/Dockerfile','-t','kavach-payment:dev','.')
        Invoke-Checked $KavachKind @('load','docker-image','kavach-payment:dev','--name','kavach-lab')
    }
    'deploy' {
        Invoke-Checked kubectl @('--kubeconfig',$KavachConfig,'--context','kind-kavach-lab','apply','-k','infrastructure/k8s/base')
        Invoke-Checked kubectl @('--kubeconfig',$KavachConfig,'--context','kind-kavach-lab','-n','kavach-lab','rollout','status','deployment/payment-api','--timeout=120s')
    }
    'status' {
        Invoke-Checked kubectl @('--kubeconfig',$KavachConfig,'--context','kind-kavach-lab','-n','kavach-lab','get','pods,svc')
    }
}
