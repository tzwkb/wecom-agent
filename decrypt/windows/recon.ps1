# 企业微信 Windows 版 · Phase0 侦察 (PowerShell, 无需 Python)
# 目的: 找数据库 + 读头部, 判断加密方案(是否同 Mac 的 wxSQLite3)。
# 特性: 只读, 不联网, 不改动任何文件。搜所有用户的 WXWork 目录。
# 用法(我从 Mac 经 SSH 跑): powershell -ExecutionPolicy Bypass -File recon.ps1
# 产出: %USERPROFILE%\recon_report.json (UTF-8), 我 scp 回来分析。
$ErrorActionPreference = 'SilentlyContinue'
$rep = [ordered]@{}

# 1. 进程 + exe 路径
$proc = Get-Process -Name WXWork, WeCom, wework -ErrorAction SilentlyContinue
$rep.processes = @($proc | Select-Object Name, Id, Path)

# 2. 安装目录
$inst = @()
foreach ($p in 'C:\Program Files\WXWork', 'C:\Program Files (x86)\WXWork',
                "$env:LOCALAPPDATA\WXWork", 'C:\Program Files\Tencent\WXWork') {
    if (Test-Path $p) { $inst += $p }
}
$rep.installs = $inst

# 3. 数据目录(所有用户 + 常见位置)
$roots = @()
$roots += Get-ChildItem 'C:\Users\*\Documents\WXWork' -Directory -ErrorAction SilentlyContinue
$roots += Get-ChildItem 'C:\Users\*\AppData\*\Tencent\WXWork' -Directory -ErrorAction SilentlyContinue
$roots = $roots | Sort-Object FullName -Unique
$rep.data_roots = @($roots.FullName)

# 4. 所有 .db → 读前 96 字节头部, 判断是否明文 SQLite / 加密
$dbs = @()
foreach ($r in $roots) {
    Get-ChildItem $r.FullName -Recurse -Filter *.db -ErrorAction SilentlyContinue | ForEach-Object {
        $fi = $_
        try {
            $fsz = $fi.Length
            if ($fsz -lt 512) { return }
            $fs = [System.IO.File]::Open($fi.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $buf = New-Object byte[] 96
            $n = $fs.Read($buf, 0, 96)
            $fs.Close()
            $hex = -join ($buf[0..([Math]::Max($n, 1) - 1)] | ForEach-Object { $_.ToString('x2') })
            $isSql = $hex.StartsWith('53514c69746520666f726d6174203300')  # "SQLite format 3\0"
            $dbs += [ordered]@{
                name = $fi.Name; path = $fi.FullName; size = $fsz
                plain_sqlite = $isSql; head96_hex = $hex
                mod4096 = ($fsz % 4096); mod1024 = ($fsz % 1024)
            }
        } catch {}
    }
}
# 重点库(消息相关)排前面
$kw = 'msg|message|session|misc|contact|info|media|fts'
$dbs = $dbs | Sort-Object @{e = { $_.name -notmatch $kw } }, @{e = { - $_.size } }
$rep.dbs = @($dbs)
$rep.db_count = $dbs.Count

# 5. 写 UTF-8 报告
$out = "$env:USERPROFILE\recon_report.json"
$json = $rep | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($out, $json, (New-Object System.Text.UTF8Encoding($false)))

# 6. ASCII 摘要(SSH 控制台不乱码)
"PROC=$($rep.processes.Count)"
"INSTALLS=$($inst.Count)"
"ROOTS=$($rep.data_roots.Count)"
"DB_COUNT=$($dbs.Count)"
"REPORT=$out"
