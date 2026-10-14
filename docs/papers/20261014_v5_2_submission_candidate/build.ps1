param([string]$TectonicPath = '')
$ErrorActionPreference = 'Stop'
if (-not $TectonicPath) {
    $taskCompiler = Get-Command tectonic -ErrorAction SilentlyContinue
    if ($taskCompiler) { $TectonicPath = $taskCompiler.Source }
    elseif ($env:CODEX_TECTONIC_PATH) { $TectonicPath = $env:CODEX_TECTONIC_PATH }
    else { throw 'Specify -TectonicPath, or install Tectonic on PATH.' }
}
if (-not (Test-Path -LiteralPath $TectonicPath -PathType Leaf)) { throw 'Tectonic executable not found.' }
Push-Location -LiteralPath $PSScriptRoot
try {
    New-Item -ItemType Directory -Path 'build' -Force | Out-Null
    & $TectonicPath -X compile CommonPose_EMBC2027_V5_2_EN.tex --outdir build --untrusted
    if ($LASTEXITCODE -ne 0) { throw 'Paper compilation failed.' }
    Write-Output 'Compiled build/CommonPose_EMBC2027_V5_2_EN.pdf'
} finally { Pop-Location }
