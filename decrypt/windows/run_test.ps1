# 企业微信 Windows 版 · 端到端测试入口
# find_key 抓 key → run_test_impl.py 跑全部命令 → 报告写到桌面
# 用法: powershell -ExecutionPolicy Bypass -File run_test.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
[Console]::OutputEncoding = [Text.Encoding]::UTF8

Write-Host "[1/2] find_key 扫内存抓 key ..." -ForegroundColor Cyan
$fk = & powershell -NoProfile -ExecutionPolicy Bypass -File "$here\find_key.ps1" 2>&1
$m = [regex]::Match((($fk | Out-String)), "KEY=([0-9a-f]{32})")
if (-not $m.Success) {
    Write-Host "✗ 抓 key 失败:" -ForegroundColor Red
    $fk
    exit 1
}
$key = $m.Groups[1].Value
Write-Host "[2/2] key=$key → 端到端测试 ..." -ForegroundColor Cyan
$env:PYTHONUTF8 = "1"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
python -X utf8 "$here\run_test_impl.py" $key "$stamp"
