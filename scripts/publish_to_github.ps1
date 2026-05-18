# One-shot: init repo (if needed), push to GitHub, trigger macOS build, print download links.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File "f:\_PERSONAL_TOOLS\MakeAGif-Webp\scripts\publish_to_github.ps1"

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
Write-Host "Repo root: $RepoRoot"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install: https://cli.github.com/"
}

$repoName = "MakeAGif-Webp"
$owner = (gh api user -q .login)
$fullName = "$owner/$repoName"

if (-not (Test-Path .git)) {
    git init -b main
    Write-Host "Initialized git repository (branch main)."
}

git add -A
$status = git status --porcelain
if ($status) {
    git commit -m "MakeAGIF v3.1.1 — sources + macOS GitHub Actions build"
    Write-Host "Committed changes."
} else {
    Write-Host "Nothing new to commit."
}

try {
    git remote get-url origin | Out-Null
} catch {
    $view = gh repo view $fullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating GitHub repo $fullName ..."
        gh repo create $repoName --public --source=. --remote=origin --description "MakeAGIF/WEBP — GIF and WebP from video (v3.1.1)"
    } else {
        git remote add origin "https://github.com/$fullName.git"
    }
}

Write-Host "Pushing to origin main..."
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Retrying push..."
    git push -u origin main
}

Write-Host "Waiting for workflow from push (or triggering manually)..."
Start-Sleep -Seconds 8
$runJson = gh run list --workflow=build.yml --limit 1 --json databaseId,url,status
$run = $runJson | ConvertFrom-Json | Select-Object -First 1
if (-not $run) {
    gh workflow run build.yml
    Start-Sleep -Seconds 8
    $runJson = gh run list --workflow=build.yml --limit 1 --json databaseId,url,status
    $run = $runJson | ConvertFrom-Json | Select-Object -First 1
}

Write-Host "Workflow: $($run.url)"
Write-Host "Waiting for build (often 15-25 min)..."
gh run watch $run.databaseId --exit-status

$tag = "v3.1.1-macos"
$zip = "MakeAGIF-v3.1.1-macOS-arm64.zip"
$releaseUrl = "https://github.com/$fullName/releases/tag/$tag"
$downloadUrl = "https://github.com/$fullName/releases/download/$tag/$zip"

Write-Host ""
Write-Host "========== DOWNLOAD LINKS =========="
Write-Host "Release page:  $releaseUrl"
Write-Host "Direct ZIP:    $downloadUrl"
Write-Host "Actions run:   $($run.url)"
Write-Host "===================================="
