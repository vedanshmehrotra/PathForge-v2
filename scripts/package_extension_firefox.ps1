$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$extensionRoot = Join-Path $repositoryRoot 'extension-firefox'
$outputRoot = Join-Path $repositoryRoot 'dist'
$names = @('manifest.json', 'background.js', 'panel.html', 'panel.css', 'panel.js', 'leetcode.js', 'icons', 'README.md', 'PRIVACY.md', 'VERIFICATION.md')
$assets = $names | ForEach-Object {
  $asset = Join-Path $extensionRoot $_
  if (!(Test-Path -LiteralPath $asset)) { throw "Missing Firefox extension asset: $_" }
  $asset
}
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$archivePath = Join-Path $outputRoot 'pathforge-extension-firefox.zip'
Compress-Archive -LiteralPath $assets -DestinationPath $archivePath -Force
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
  if (!($archive.Entries.FullName -contains 'manifest.json')) { throw 'The archive manifest is not at its root.' }
  if ($archive.Entries.FullName | Where-Object { $_ -match '(node_modules|\.next|pathforge-frontend|verify_extension|service-worker)' }) {
    throw 'The archive includes a non-Firefox artifact.'
  }
  Write-Output ("Created {0} ({1} files). Upload this ZIP to Mozilla; it is not yet signed." -f $archivePath, $archive.Entries.Count)
} finally { $archive.Dispose() }
