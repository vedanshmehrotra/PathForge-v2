$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$extensionRoot = Join-Path $repositoryRoot 'extension'
$outputRoot = Join-Path $repositoryRoot 'dist'
$names = @('manifest.json', 'panel.html', 'panel.css', 'panel.js', 'leetcode.js', 'service-worker.js', 'icons', 'README.md', 'VERIFICATION.md')
$assets = $names | ForEach-Object {
  $asset = Join-Path $extensionRoot $_
  if (!(Test-Path -LiteralPath $asset)) { throw "Missing extension asset: $_" }
  $asset
}
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$archivePath = Join-Path $outputRoot 'pathforge-extension-chrome.zip'
Compress-Archive -LiteralPath $assets -DestinationPath $archivePath -Force
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
  if (!($archive.Entries.FullName -contains 'manifest.json')) { throw 'The archive manifest is not at its root.' }
  if ($archive.Entries.FullName | Where-Object { $_ -match '(node_modules|\.next|pathforge-frontend|verify_extension)' }) {
    throw 'The archive includes a non-extension artifact.'
  }
  Write-Output ("Created {0} ({1} files). Extract it before loading in Chrome." -f $archivePath, $archive.Entries.Count)
} finally { $archive.Dispose() }
