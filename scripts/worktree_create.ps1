param(
  [Parameter(Mandatory = $true)]
  [int]$Issue,

  [Parameter(Mandatory = $true)]
  [string]$Slug,

  [Parameter(Mandatory = $true)]
  [ValidateSet("frontend", "backend", "ops-quality")]
  [string]$Lane,

  [string]$Base = "master"
)

$ErrorActionPreference = "Stop"

$commonGitDir = (git rev-parse --path-format=absolute --git-common-dir).Trim()
if (-not $commonGitDir) {
  throw "Nao foi possivel localizar o git common dir do repositorio."
}

$repoRoot = Split-Path $commonGitDir -Parent
if (-not $repoRoot) {
  throw "Nao foi possivel localizar a raiz do repositorio."
}

$branch = "task/$Issue-$Slug"
$relativePath = ".claude/worktrees/$Lane/$Issue-$Slug"
$worktreePath = Join-Path $repoRoot $relativePath

$existingWorktreePattern = [regex]::Escape($worktreePath)
$existingWorktree = git -C $repoRoot worktree list --porcelain | Select-String -Pattern $existingWorktreePattern
if ($existingWorktree) {
  Write-Output "Worktree ja existe: $worktreePath"
  Write-Output "Branch: $branch"
  Write-Output "Abra em outra janela do VS Code:"
  Write-Output "code `"$worktreePath`""
  exit 0
}

New-Item -ItemType Directory -Force -Path (Split-Path $worktreePath) | Out-Null

$existingBranch = git -C $repoRoot branch --list $branch
if ($existingBranch) {
  git -C $repoRoot worktree add $worktreePath $branch | Out-Null
} else {
  git -C $repoRoot worktree add -b $branch $worktreePath $Base | Out-Null
}

Write-Output "Worktree criada com sucesso."
Write-Output "Branch: $branch"
Write-Output "Path: $worktreePath"
Write-Output "Abra em outra janela do VS Code:"
Write-Output "code `"$worktreePath`""
