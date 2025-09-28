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

# Export mapping temporarily so SyncPvmEnvs.ps1 can use it
$mappingPath = Join-Path $env:TEMP "pvm-mapping-$pid.json"
$mapping | ConvertTo-Json -Depth 10 | Set-Content $mappingPath

Write-Step "Creating worktree: $WorktreePath for branch $Branch"
if (-not $WhatIf) {
  git worktree add $WorktreePath -b $Branch
  if ($LASTEXITCODE -ne 0) { throw "git worktree add failed." }
}

Write-Step "Syncing .env and .env.test files from $SecretsRoot"
& (Join-Path $PSScriptRoot "SyncPvmEnvs.ps1") -WorktreePath $WorktreePath -SecretsRoot $SecretsRoot -MappingJson $mappingPath -Force:$Force -WhatIf:$WhatIf

# Clean up temporary mapping file
if (Test-Path $mappingPath) {
  Remove-Item $mappingPath -Force
  Write-Step "Cleaned up temporary mapping file"
}

Write-Step "Done."

#.\gittools\NewPvmWorktree.ps1 -WorktreePath ..\feat-integrate-tiktok-search -Branch feat/integrate-tiktok-search 
