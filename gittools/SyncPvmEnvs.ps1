param(
  [string]$WorktreePath = (Get-Location).Path,
  [string]$SecretsRoot = 'O:\product-video-matching\secrets',
  [switch]$Force,
  [switch]$WhatIf
)

function Copy-EnvFile {
  param(
    [string]$TargetDir,
    [string]$SecretFile,
    [string]$FileExtension = 'env'
  )

  $dest   = if ($FileExtension -eq 'test') {
    Join-Path $TargetDir ".env.test"
  } else {
    Join-Path $TargetDir ".$FileExtension"
  }

  # For .env.test files, construct the source file name differently
  if ($FileExtension -eq 'test') {
    $envFile = $SecretFile.Replace('.env', '')
    $source = Join-Path $SecretsRoot "$envFile.env.test"

    # Only warn for missing test files if the original secret file was a .env file
    if (-not (Test-Path $source) -and $SecretFile -like "*.env") {
      Write-Warning "Missing test secret file: $source"
      return
    }
  } else {
    # For .env files, warn if missing
    $source = Join-Path $SecretsRoot $SecretFile
    if (-not (Test-Path $source)) {
      Write-Warning "Missing secret file: $source";
      return
    }
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
    $fileType = if ($FileExtension -eq 'test') { '.env.test' } else { '.env' }
    Write-Host "Copy: $source -> $dest" -ForegroundColor Green
    if (-not $WhatIf) { Copy-Item $source $dest -Force }
  }
}

# Default mapping (same as the creator script)
$mapping = [ordered]@{
  'services\main-api'              = 'main-api.env'
  'infra\pvm'                      = 'infra-pvm.env'
  'tests'                          = 'infra-pvm.env'
  'services\video-crawler'         = 'video-crawler.env'
  'services\dropship-product-finder' = 'dropship-product-finder.env'
  'services\product-segmentor'     = 'product-segmentor.env'
  'services\vision-keypoint'       = 'vision-keypoint.env'
  'services\front-end'             = 'front-end.env'
}


Write-Host "==> Syncing .env and .env.test into $WorktreePath from $SecretsRoot" -ForegroundColor Cyan
foreach ($kv in $mapping.GetEnumerator()) {
  $target = Join-Path $WorktreePath $kv.Key

  # Copy .env file
  Copy-EnvFile -TargetDir $target -SecretFile $kv.Value -FileExtension 'env'

  # Copy corresponding .env.test file
  Copy-EnvFile -TargetDir $target -SecretFile $kv.Value -FileExtension 'test'
}
Write-Host "==> Done." -ForegroundColor Cyan

# .\gittools\SyncPvmEnvs.ps1