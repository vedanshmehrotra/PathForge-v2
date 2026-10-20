param([string]$BrowserExecutable = '')
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$extensionRoot = Join-Path $repositoryRoot 'extension'
$reviewRoot = Join-Path $repositoryRoot '.playwright-cli\extension-review'
$cli = (Get-Command playwright-cli -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $reviewRoot -Force | Out-Null
$launch = @{
  channel = 'chromium'
  headless = $true
  args = @("--disable-extensions-except=$extensionRoot", "--load-extension=$extensionRoot")
}
if ($BrowserExecutable) {
  if (!(Test-Path -LiteralPath $BrowserExecutable -PathType Leaf)) { throw 'BrowserExecutable does not exist.' }
  $launch.executablePath = $BrowserExecutable
}
$config = @{
  browser = @{
    browserName = 'chromium'
    userDataDir = (Join-Path $reviewRoot 'profile')
    launchOptions = $launch
    contextOptions = @{ viewport = @{ width = 400; height = 900 } }
  }
  outputDir = $reviewRoot
}
$configPath = Join-Path $reviewRoot 'config.json'
$config | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $configPath -Encoding utf8
Push-Location $repositoryRoot
try {
  & $cli -s=pathforge-extension-review open --config=$configPath
  if ($LASTEXITCODE -ne 0) { throw 'Could not launch the isolated extension browser.' }
  $resultText = (& $cli -s=pathforge-extension-review --raw run-code --filename='scripts/verify_extension_browser.js') -join "`n"
  if ($LASTEXITCODE -ne 0) { throw "The extension browser checks failed: $resultText" }
  $result = $resultText | ConvertFrom-Json -ErrorAction Stop
  if (!$result.passed -or $result.passed -ne $result.checks.Count) { throw 'The browser checks did not return a complete passing report.' }
  $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reviewRoot 'report.json') -Encoding utf8
  Write-Output ("Passed {0} extension browser checks. Authenticated API responses were controlled fixtures." -f $result.passed)
  Write-Output ("Report and screenshots: {0}" -f $reviewRoot)
} finally {
  & $cli -s=pathforge-extension-review close
  Pop-Location
}
