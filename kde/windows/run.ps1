[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Python = 'python',
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$AppArgs
)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$venvPython = Join-Path $appRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $appRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Install Python 3.10 or newer (64 bit).' }
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the Windows dependencies.' }
}
$oldPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $appRoot
    & $venvPython -m refract @AppArgs
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $oldPath
}
