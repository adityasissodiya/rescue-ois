[CmdletBinding()]
param()

# Builds the scenario and system model document (handoff 1) into model/build/.
# Two pdflatex passes resolve the cross-references; the document has no bibliography.

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

$pdfLaTeX = Resolve-LaTeXTool -Name 'pdflatex'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$pdfArguments = @(
    '--enable-installer'
    '-interaction=nonstopmode'
    '-file-line-error'
    '-halt-on-error'
    "-output-directory=$outputDirectory"
    'scenario-and-model.tex'
)

Push-Location $projectRoot
try {
    foreach ($pass in 1..2) {
        & $pdfLaTeX @pdfArguments
        if ($LASTEXITCODE -ne 0) {
            throw "pdflatex failed with exit code $LASTEXITCODE on pass $pass"
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Built $outputDirectory\scenario-and-model.pdf"
