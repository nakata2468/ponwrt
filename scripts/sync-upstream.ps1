[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $dirty = @(git status --porcelain)
    if ($dirty.Count -gt 0) {
        Write-Output "WORKTREE_DIRTY"
        Write-Output "Commit, stash, or resolve local changes before syncing upstream."
        exit 1
    }

    $remotes = @(git remote)
    if ($remotes -notcontains "upstream") {
        git remote add upstream https://github.com/pbs05/ponwrt.git
    }

    git fetch upstream master
    if ($LASTEXITCODE -ne 0) {
        Write-Output "UPSTREAM_FETCH_FAILED"
        exit 1
    }

    $newCount = [int](git rev-list --count "HEAD..upstream/master")
    if ($newCount -eq 0) {
        Write-Output "NO_UPSTREAM_CHANGES"
        exit 2
    }

    Write-Output "NEW_UPSTREAM_COMMITS=$newCount"
    git merge --no-edit upstream/master
    if ($LASTEXITCODE -ne 0) {
        Write-Output "UPSTREAM_MERGE_CONFLICT"
        Write-Output "Resolve conflicts while preserving configs/release.config and the AN7581-only release workflow."
        exit 1
    }

    Write-Output "MERGED_UPSTREAM_CHANGES"
}
finally {
    Pop-Location
}