param(
    [Parameter(Mandatory=$true)][string]$StateDb,
    [Parameter(Mandatory=$true)][string]$ProjectDir,
    [int]$Port = 8515
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
function Test-FullyQualifiedWindowsPath([string]$Value) {
    return $Value -match '^(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\[^\\]+(?:\\|$))'
}
if (-not (Test-FullyQualifiedWindowsPath $StateDb) -or -not (Test-FullyQualifiedWindowsPath $ProjectDir)) {
    throw 'StateDb and ProjectDir must be absolute paths; no current-directory fallback.'
}
if (-not (Test-Path -LiteralPath $StateDb -PathType Leaf)) {
    throw 'Original state database does not exist; refusing to create an empty replacement.'
}
if (-not (Test-Path -LiteralPath $ProjectDir -PathType Container)) {
    throw 'Project directory does not exist.'
}
Set-Location -LiteralPath $repoPath
$env:PYTHONPATH = Join-Path $repoPath 'src'
$env:FFA_WORKSPACE_STATE_DB = (Resolve-Path -LiteralPath $StateDb).Path
$env:FFA_WORKSPACE_PROJECT_DIR = (Resolve-Path -LiteralPath $ProjectDir).Path
$env:FFA_WORKSPACE_TENANT = 'default'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
Write-Output "State database: $env:FFA_WORKSPACE_STATE_DB"
Write-Output "Project: $env:FFA_WORKSPACE_PROJECT_DIR; tenant: default; port: $Port"
& (Join-Path $repoPath '.venv/Scripts/python.exe') -m streamlit run (Join-Path $repoPath 'apps/streamlit_app.py') --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false
exit $LASTEXITCODE
