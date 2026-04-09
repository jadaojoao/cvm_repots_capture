$ErrorActionPreference = "Stop"

$commonGitDir = (git rev-parse --path-format=absolute --git-common-dir).Trim()
if (-not $commonGitDir) {
  throw "Nao foi possivel localizar o git common dir do repositorio."
}

$repoRoot = Split-Path $commonGitDir -Parent
if (-not $repoRoot) {
  throw "Nao foi possivel localizar a raiz do repositorio."
}

$mainBranch = (git -C $repoRoot branch --show-current).Trim()
$items = @()
$current = @{}

foreach ($line in (git -C $repoRoot worktree list --porcelain)) {
  if ($line -like "worktree *") {
    if ($current.Count -gt 0) {
      $items += [pscustomobject]$current
    }
    $current = @{
      Worktree = $line.Substring(9)
      Branch = ""
      Head = ""
      Bare = $false
      Detached = $false
    }
    continue
  }

  if ($line -like "branch *") {
    $current.Branch = $line.Substring(7).Replace("refs/heads/", "")
    continue
  }

  if ($line -like "HEAD *") {
    $current.Head = $line.Substring(5)
    continue
  }

  if ($line -eq "bare") {
    $current.Bare = $true
    continue
  }

  if ($line -eq "detached") {
    $current.Detached = $true
  }
}

if ($current.Count -gt 0) {
  $items += [pscustomobject]$current
}

Write-Output "Main worktree branch: $mainBranch"
$items | Sort-Object Worktree | Format-Table Worktree, Branch, Head, Detached -AutoSize
