param(
  [Parameter(Mandatory = $true)]
  [int]$Pr,

  [ValidateSet("squash", "merge", "rebase")]
  [string]$Method = "squash",

  [int]$PollSeconds = 10,

  [int]$TimeoutSeconds = 1800,

  [switch]$SkipRemoteDelete
)

$ErrorActionPreference = "Stop"

function Get-PrData {
  param([int]$Number)

  $json = gh pr view $Number --json number,state,isDraft,url,headRefName,body
  if (-not $json) {
    throw "Nao foi possivel ler os dados da PR #$Number."
  }

  return $json | ConvertFrom-Json
}

function Get-LinkedIssues {
  param([string]$Body)

  $matches = [regex]::Matches($Body, '(?im)\bCloses\s+#(\d+)\b')
  $issues = @()
  foreach ($match in $matches) {
    $issues += [int]$match.Groups[1].Value
  }

  return $issues | Sort-Object -Unique
}

function Confirm-IssuesClosed {
  param([int[]]$IssueNumbers)

  foreach ($issueNumber in $IssueNumbers) {
    $issue = gh issue view $issueNumber --json state | ConvertFrom-Json
    if ($issue.state -ne "CLOSED") {
      throw "A issue #$issueNumber ainda nao fechou depois do merge da PR."
    }
  }
}

function Remove-RemoteBranchIfNeeded {
  param([string]$BranchName)

  if (-not $BranchName) {
    return
  }

  $remoteBranch = git ls-remote --heads origin $BranchName
  if (-not $remoteBranch) {
    return
  }

  git push origin --delete $BranchName | Out-Null
}

$prData = Get-PrData -Number $Pr

if ($prData.state -eq "MERGED") {
  $linkedIssues = Get-LinkedIssues -Body $prData.body
  if ($linkedIssues.Count -eq 0) {
    throw "A PR #$Pr ja esta mergeada, mas nao foi encontrado nenhum 'Closes #<issue>' no corpo."
  }

  Confirm-IssuesClosed -IssueNumbers $linkedIssues

  if (-not $SkipRemoteDelete) {
    Remove-RemoteBranchIfNeeded -BranchName $prData.headRefName
  }

  Write-Output "PR #$Pr ja estava mergeada e a issue vinculada esta fechada."
  exit 0
}

if ($prData.state -ne "OPEN") {
  throw "A PR #$Pr esta em estado '$($prData.state)' e nao pode ser concluida."
}

if ($prData.isDraft) {
  gh pr ready $Pr | Out-Null
  $prData = Get-PrData -Number $Pr
}

$mergeArgs = @("pr", "merge", $Pr.ToString(), "--auto")
switch ($Method) {
  "squash" { $mergeArgs += "--squash" }
  "merge" { $mergeArgs += "--merge" }
  "rebase" { $mergeArgs += "--rebase" }
}
gh @mergeArgs | Out-Null

gh pr checks $Pr --required --watch --fail-fast --interval $PollSeconds | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
  $prData = Get-PrData -Number $Pr

  if ($prData.state -eq "MERGED") {
    break
  }

  if ($prData.state -ne "OPEN") {
    throw "A PR #$Pr mudou para o estado '$($prData.state)' antes do merge."
  }

  Start-Sleep -Seconds $PollSeconds
} while ((Get-Date) -lt $deadline)

if ($prData.state -ne "MERGED") {
  throw "A PR #$Pr nao apareceu como mergeada dentro do timeout de $TimeoutSeconds segundos."
}

$linkedIssues = Get-LinkedIssues -Body $prData.body
if ($linkedIssues.Count -eq 0) {
  throw "A PR #$Pr foi mergeada, mas nao foi encontrado nenhum 'Closes #<issue>' no corpo."
}

Confirm-IssuesClosed -IssueNumbers $linkedIssues

if (-not $SkipRemoteDelete) {
  Remove-RemoteBranchIfNeeded -BranchName $prData.headRefName
}

Write-Output "PR #$Pr mergeada com sucesso."
Write-Output "Issues fechadas: $($linkedIssues -join ', ')"
Write-Output "Branch remota tratada: $($prData.headRefName)"
