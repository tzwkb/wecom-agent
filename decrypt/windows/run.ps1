# 企业微信 Windows 版 · 一键入口 —— find_key 抓 key → wecom_win 跑子命令
# 用法: powershell -ExecutionPolicy Bypass -File run.ps1 <子命令> [参数]
#   子命令: read | contacts [词] | conversations | search <词> | stats | todo
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[1/2] 扫内存抓 key ..." -ForegroundColor Cyan
$fk = & powershell -NoProfile -ExecutionPolicy Bypass -File "$here\find_key.ps1" 2>&1
$m = [regex]::Match((($fk | Out-String)), "KEY=([0-9a-f]{32})")
if (-not $m.Success) {
    Write-Host "✗ 抓 key 失败:" -ForegroundColor Red
    $fk
    exit 1
}
$key = $m.Groups[1].Value
Write-Host "[2/2] key=$key → wecom_win $($Rest -join ' ')" -ForegroundColor Cyan
$env:PYTHONUTF8 = "1"
python -X utf8 "$here\wecom_win.py" $key @Rest
