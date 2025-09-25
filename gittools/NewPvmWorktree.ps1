param(
  [Parameter(Mandatory=$true)][string]$Branch,
  [Parameter(Mandatory=$true)][string]$WorktreePath,   # e.g. O:\product-video-matching\feat-my-branch
  [string]$RepoRoot = $(git rev-parse --show-toplevel 2>$null),
  [string]$SecretsRoot = 'O:\product-video-matching\secrets',
  [string]$MappingJson = '',                           # optional: path to mapping json
  [switch]$Force,                                      # overwrite .env if present
  [switch]$WhatIf                                      # dry run
)

if (-not $RepoRoot) { throw "RepoRoot not detected. Run inside a git repo or pass -RepoRoot." }
if (-not (Test-Path $SecretsRoot)) { throw "SecretsRoot not found: $SecretsRoot" }

function Write-Step([string]$msg){ Write-Host "==> $msg" -ForegroundColor Cyan }
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
    $msg = if ($Force) { "Copy (force)" } else { "Copy" }
    Write-Host "$($msg): $source -> $dest" -ForegroundColor Green
    if (-not $WhatIf) { Copy-Item $source $dest -Force }
  }
}

# Default mapping: relative folder -> secret filename in SecretsRoot
$mapping = [ordered]@{
  'services\main-api'              = 'main-api.env'               # you stated main-api uses main.env
  'infra\pvm'                      = 'infra-pvm.env'          # main app env lives here
  'services\video-crawler'         = 'video-crawler.env'
  'services\dropship-product-finder' = 'dropship-product-finder.env'
  'services\product-segmentor'     = 'product-segmentor.env'
  'services\vision-keypoint'       = 'vision-keypoint.env'
  'services\front-end'             = 'front-end.env'
}

# Optional: load a custom mapping json like:
# { "services/main-api": "main.env", "infra/pvm": "infra-pvm.env" }
if ($MappingJson) {
  if (-not (Test-Path $MappingJson)) { throw "MappingJson not found: $MappingJson" }
  $jsonMap = Get-Content $MappingJson -Raw | ConvertFrom-Json
  $mapping = @{}
  foreach ($k in $jsonMap.PSObject.Properties.Name) {
    $mapping[$k -replace '/','\'] = $jsonMap.$k
  }
}

Write-Step "Creating worktree: $WorktreePath for branch $Branch"
if (-not $WhatIf) {
  git worktree add $WorktreePath -b $Branch
  if ($LASTEXITCODE -ne 0) { throw "git worktree add failed." }
}

Write-Step "Syncing .env files from $SecretsRoot"
foreach ($kv in $mapping.GetEnumerator()) {
  $relDir = $kv.Key
  $secret = $kv.Value
  $target = Join-Path $WorktreePath $relDir
  Copy-EnvFile -TargetDir $target -SecretFile $secret
}

Write-Step "Done."

#.\gittools\NewPvmWorktree.ps1 -WorktreePath ..\feat-integrate-tiktok-search -Branch feat/integrate-tiktok-search 
