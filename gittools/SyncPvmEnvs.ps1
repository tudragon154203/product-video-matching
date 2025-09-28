param(
  [string]$WorktreePath = (Get-Location).Path,
  [string]$SecretsRoot = 'O:\product-video-matching\secrets',
  [string]$MappingJson = '',
  [switch]$Force,
  [switch]$WhatIf
)

function Copy-EnvFile {
  param([string]$TargetDir, [string]$SecretFile)
  $source = Join-Path $SecretsRoot $SecretFile
  $dest   = Join-Path $TargetDir ".env"

  if (-not (Test-Path $source)) { Write-Warning "Missing secret file: $source"; return }
  if (-not (Test-Path $TargetDir)) { New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null }

  if ((Test-Path $dest) -and -not $Force) {
    Write-Host "Skip (exists): $dest" -ForegroundColor Yellow
  } else {
    if ((Test-Path $dest) -and $Force) {
      $bak = "$dest.bak.$([DateTime]::Now.ToString('yyyyMMdd-HHmmss'))"
      if (-not $WhatIf) { Copy-Item $dest $bak -Force }
      Write-Host "Backup: $dest -> $bak" -ForegroundColor DarkYellow
    }
    Write-Host "Copy: $source -> $dest" -ForegroundColor Green
    if (-not $WhatIf) { Copy-Item $source $dest -Force }
  }
}

function Copy-EnvTestFile {
  param([string]$TargetDir, [string]$SecretFile)
  $envFile = $SecretFile.Replace('.env', '')
  $source = Join-Path $SecretsRoot "$envFile.env.test"
  $dest   = Join-Path $TargetDir ".env.test"

  if (-not (Test-Path $source)) {
    if ($SecretFile -like "*.env") {
      # Only warn if this is a .env file (not already .env.test)
      Write-Warning "Missing test secret file: $source"
    }
    return
  }
  if (-not (Test-Path $TargetDir)) { New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null }

  if ((Test-Path $dest) -and -not $Force) {
    Write-Host "Skip (exists): $dest" -ForegroundColor Yellow
  } else {
    if ((Test-Path $dest) -and $Force) {
      $bak = "$dest.bak.$([DateTime]::Now.ToString('yyyyMMdd-HHmmss'))"
      if (-not $WhatIf) { Copy-Item $dest $bak -Force }
      Write-Host "Backup: $dest -> $bak" -ForegroundColor DarkYellow
    }
    Write-Host "Copy: $source -> $dest" -ForegroundColor Green
    if (-not $WhatIf) { Copy-Item $source $dest -Force }
  }
}

# Default mapping (same as the creator script)
$mapping = [ordered]@{
  'services\main-api'              = 'main-api.env'
  'infra\pvm'                      = 'infra-pvm.env'
  'services\video-crawler'         = 'video-crawler.env'
  'services\dropship-product-finder' = 'dropship-product-finder.env'
  'services\product-segmentor'     = 'product-segmentor.env'
  'services\vision-keypoint'       = 'vision-keypoint.env'
  'services\front-end'             = 'front-end.env'
}

if ($MappingJson) {
  if (-not (Test-Path $MappingJson)) { throw "MappingJson not found: $MappingJson" }
  $jsonMap = Get-Content $MappingJson -Raw | ConvertFrom-Json
  $mapping = @{}
  foreach ($k in $jsonMap.PSObject.Properties.Name) {
    $mapping[$k -replace '/','\'] = $jsonMap.$k
  }
}

Write-Host "==> Syncing .env and .env.test into $WorktreePath from $SecretsRoot" -ForegroundColor Cyan
foreach ($kv in $mapping.GetEnumerator()) {
  $target = Join-Path $WorktreePath $kv.Key

  # Copy .env file
  Copy-EnvFile -TargetDir $target -SecretFile $kv.Value

  # Copy corresponding .env.test file
  Copy-EnvTestFile -TargetDir $target -SecretFile $kv.Value
}
Write-Host "==> Done." -ForegroundColor Cyan

# .\gittools\SyncPvmEnvs.ps1