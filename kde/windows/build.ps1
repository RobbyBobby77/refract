[CmdletBinding()]
param([string]$Python = 'python', [string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$venvPython = Join-Path $appRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $appRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10 or newer (64 bit).' }
}
& $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt') 'pyinstaller==6.22.3'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PSScriptRoot 'dist' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$buildRoot = Join-Path $PSScriptRoot 'build'
& $venvPython (Join-Path $PSScriptRoot 'make-icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
$originalBuildPath = $env:PATH
# Foreign Qt/ICU DLLs on PATH can be mistaken for Windows system dependencies.
# Resolve dependencies against Python, bundled Qt and Windows itself.
$pythonRoot = & $venvPython -c 'import sys; print(sys.base_prefix)'
$env:PATH = "$pythonRoot;$pythonRoot\DLLs;$env:SystemRoot\System32;$env:SystemRoot"
try {
& $venvPython -m PyInstaller --noconfirm --clean --onedir --windowed --name Refract `
    --paths $appRoot --icon (Join-Path $buildRoot 'refract.ico') `
    --add-data "$(Join-Path $appRoot 'refract\qml');refract/qml" `
    --add-data "$(Join-Path $appRoot 'refract\shaders');refract/shaders" `
    --add-data "$(Join-Path $appRoot 'refract\fonts');refract/fonts" `
    --add-data "$(Join-Path $appRoot 'refract\icons');refract/icons" `
    --distpath $OutputDirectory --workpath (Join-Path $buildRoot 'pyinstaller') --specpath $buildRoot `
    (Join-Path $PSScriptRoot 'entry.py')
if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed.' }
} finally {
    $env:PATH = $originalBuildPath
}
$bundle = Join-Path $OutputDirectory 'Refract'
Copy-Item -LiteralPath (Join-Path $appRoot '..\COPYING') -Destination (Join-Path $bundle 'COPYING.txt')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md') -Destination (Join-Path $bundle 'README.md')
# Include third-party notices supplied by Qt, psutil and the font package.
& $venvPython (Join-Path $PSScriptRoot 'licenses.py') $bundle
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
$zipPath = Join-Path $OutputDirectory 'Refract-Windows-x64.zip'
Compress-Archive -LiteralPath $bundle -DestinationPath $zipPath -Force
Write-Host "Built $zipPath"
