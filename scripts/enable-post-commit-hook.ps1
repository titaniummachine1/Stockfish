# One-time: use repo hooks that build+test after each commit
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root
git config core.hooksPath .githooks
Write-Host "core.hooksPath set to .githooks (post-commit build+test enabled)"
