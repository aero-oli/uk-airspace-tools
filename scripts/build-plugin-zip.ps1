param(
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pluginDir = Join-Path $repoRoot "uk_airspace_tools"
$outputDirPath = Join-Path $repoRoot $OutputDirectory
$zipPath = Join-Path $outputDirPath "uk_airspace_tools.zip"
$stagingRoot = Join-Path $outputDirPath "_staging"
$stagingPlugin = Join-Path $stagingRoot "uk_airspace_tools"

if (-not (Test-Path $pluginDir)) {
    throw "Plugin directory not found: $pluginDir"
}

New-Item -ItemType Directory -Force -Path $outputDirPath | Out-Null
if (Test-Path $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
Copy-Item -LiteralPath $pluginDir -Destination $stagingPlugin -Recurse

Get-ChildItem -Path $stagingPlugin -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $stagingPlugin -Recurse -Include "*.pyc", "*.pyo", "*.gpkg", "*.gpkg-*" | Remove-Item -Force

Compress-Archive -Path $stagingPlugin -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $stagingRoot -Recurse -Force

Write-Output "Created $zipPath"
