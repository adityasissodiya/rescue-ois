[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$outputDirectory = Join-Path $projectRoot 'build'
$miKTeXBin = Join-Path $env:LOCALAPPDATA 'Programs\MiKTeX\miktex\bin\x64'

function Resolve-LaTeXTool {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidate = Join-Path $miKTeXBin "$Name.exe"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }

    throw "Could not find $Name. Install MiKTeX or add its bin directory to PATH."
}

function Invoke-LaTeXTool {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Build command failed with exit code $LASTEXITCODE`: $Executable"
    }
}

$pdfLaTeX = Resolve-LaTeXTool -Name 'pdflatex'
$bibTeX = Resolve-LaTeXTool -Name 'bibtex'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$pdfArguments = @(
    '--enable-installer'
    '-synctex=1'
    '-interaction=nonstopmode'
    '-file-line-error'
    '-halt-on-error'
    "-output-directory=$outputDirectory"
    'main.tex'
)

Push-Location $projectRoot
try {
    Invoke-LaTeXTool -Executable $pdfLaTeX -Arguments $pdfArguments
    Invoke-LaTeXTool -Executable $bibTeX -Arguments @('--enable-installer', 'build/main')
    Invoke-LaTeXTool -Executable $pdfLaTeX -Arguments $pdfArguments
    Invoke-LaTeXTool -Executable $pdfLaTeX -Arguments $pdfArguments
}
finally {
    Pop-Location
}

Write-Host "Built $outputDirectory\main.pdf"
