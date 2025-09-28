param(
  [Parameter(Mandatory=$true)][string]$Branch,
  [Parameter(Mandatory=$true)][string]$WorktreePath,   # e.g. O:\product-video-matching\feat-my-branch
  [string]$RepoRoot = $(git rev-parse --show-toplevel 2>$null),
  [string]$SecretsRoot = 'O:\product-video-matching\secrets',
  [switch]$Force,                                      # overwrite .env if present
  [switch]$WhatIf                                      # dry run
)

if (-not $RepoRoot) { throw "RepoRoot not detected. Run inside a git repo or pass -RepoRoot." }
if (-not (Test-Path $SecretsRoot)) { throw "SecretsRoot not found: $SecretsRoot" }

function Write-Step([string]$msg){ Write-Host "==> $msg" -ForegroundColor Cyan }


Write-Step "Creating worktree: $WorktreePath for branch $Branch"
if (-not $WhatIf) {
  git worktree add $WorktreePath -b $Branch
  if ($LASTEXITCODE -ne 0) { throw "git worktree add failed." }
}

Write-Step "Syncing .env and .env.test files from $SecretsRoot"
& (Join-Path $PSScriptRoot "SyncPvmEnvs.ps1") -WorktreePath $WorktreePath -SecretsRoot $SecretsRoot -Force:$Force -WhatIf:$WhatIf

Write-Step "Done."

#.\gittools\NewPvmWorktree.ps1 -WorktreePath ..\feat-integrate-tiktok-search -Branch feat/integrate-tiktok-search 
