$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$KavachArgs = @('--kubeconfig','infrastructure/kubeconfig','--context','kind-kavach-lab')
kubectl @KavachArgs apply -k infrastructure/k8s/monitoring/metrics-server
if ($LASTEXITCODE -ne 0) { throw 'metrics-server apply failed' }
kubectl @KavachArgs apply -k infrastructure/k8s/monitoring
if ($LASTEXITCODE -ne 0) { throw 'monitoring apply failed' }
foreach ($KavachDeployment in @('prometheus','grafana')) {
    kubectl @KavachArgs -n kavach-lab rollout status "deployment/$KavachDeployment" --timeout=180s
    if ($LASTEXITCODE -ne 0) { throw "$KavachDeployment rollout failed" }
}
kubectl @KavachArgs -n kube-system rollout status deployment/metrics-server --timeout=180s
if ($LASTEXITCODE -ne 0) { throw 'metrics-server rollout failed' }
