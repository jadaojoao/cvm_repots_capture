param(
  [Parameter(Mandatory = $true)]
  [int]$Issue,

  [Parameter(Mandatory = $true)]
  [string]$Slug,

  [Parameter(Mandatory = $true)]
  [ValidateSet("frontend", "backend", "ops-quality")]
  [string]$Lane,

  [string]$Base = "master",

  [switch]$Force
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

if (-not (Test-Path $worktreePath)) {
  throw "Worktree nao encontrada: $worktreePath"
}

if (-not $Force) {
  $merged = (git -C $repoRoot branch --merged $Base --list $branch).Trim()
  if (-not $merged) {
    throw "A branch $branch ainda nao aparece como mergeada em $Base. Use -Force para remover mesmo assim."
  }
}

$removeArgs = @("worktree", "remove")
if ($Force) {
  $removeArgs += "--force"
}
$removeArgs += $worktreePath

git -C $repoRoot @removeArgs | Out-Null
git -C $repoRoot worktree prune | Out-Null

Write-Output "Worktree removida: $worktreePath"
Write-Output "Branch local preservada: $branch"
