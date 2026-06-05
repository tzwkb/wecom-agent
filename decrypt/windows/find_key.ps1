# 企业微信 Windows 版 · key 提取 (PowerShell + 内嵌 C#, 免装 Python)
# 扫 WXWork.exe 进程可写私有内存, 找 16 字节 wxSQLite3 key。
# 校验算法 = Mac wxwork_crypto.quick_verify 的移植 (针对 message.db 页1)。
# 常量(由 Mac 端算出, 见 windows/NOTES.md):
#   FRAG   = page1[16:24]                  10 00 02 02 00 40 20 20
#   CIPHER = page1[8:16]+page1[24:32]      e0a5c9b8d5fcac64 f9d9a69aaaca806b
#   IV     = generate_initial_vector(1)    20d7420f9c37a35dca6fe92a1c6999a9
#   后缀 SUF = 01000000 + "sAlT"(73416c54) 接在候选 key 后做 md5
# 用法(我从 Mac 经 SSH): powershell -ExecutionPolicy Bypass -File find_key.ps1
$ErrorActionPreference = 'Continue'

$cs = @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;

public class KeyScan {
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr OpenProcess(uint a, bool inh, int pid);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll", SetLastError=true)] static extern long VirtualQueryEx(IntPtr h, IntPtr addr, out MBI mbi, uint len);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, IntPtr size, out IntPtr read);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr h, uint acc, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool LookupPrivilegeValue(string s, string n, out long luid);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr tok, bool dis, ref TP newp, uint len, IntPtr prev, IntPtr ret);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();

    [StructLayout(LayoutKind.Sequential)] struct MBI {
        public IntPtr BaseAddress, AllocationBase;
        public uint AllocationProtect, __a1;
        public IntPtr RegionSize;
        public uint State, Protect, Type, __a2;
    }
    [StructLayout(LayoutKind.Sequential)] struct TP { public uint Count; public long Luid; public uint Attr; }

    const uint MEM_COMMIT=0x1000, MEM_PRIVATE=0x20000;
    const uint PAGE_RW=0x04, PAGE_WC=0x08, PAGE_GUARD=0x100, PAGE_NOACCESS=0x01;

    static byte[] FRAG, CIPHER, IV, SUF;
    static MD5 md5 = MD5.Create();
    static Aes AES;

    public static void EnableDebug() {
        IntPtr tok; if (!OpenProcessToken(GetCurrentProcess(), 0x20|0x08, out tok)) return;
        long luid; if (!LookupPrivilegeValue(null, "SeDebugPrivilege", out luid)) return;
        TP tp = new TP(); tp.Count=1; tp.Luid=luid; tp.Attr=0x2; // SE_PRIVILEGE_ENABLED
        AdjustTokenPrivileges(tok, false, ref tp, 0, IntPtr.Zero, IntPtr.Zero);
    }

    static int PC(ulong x){ int c=0; while(x!=0){ x&=x-1; c++; } return c; }

    static bool Hit(byte[] b, int o) {
        ulong m0=0,m1=0,m2=0,m3=0; int na=0;
        for (int j=0;j<16;j++){
            byte v=b[o+j];
            int w=v>>6; ulong bit=1UL<<(v&63);
            if(w==0)m0|=bit; else if(w==1)m1|=bit; else if(w==2)m2|=bit; else m3|=bit;
            if(v<0x20||v>0x7e) na++;
        }
        if (na<3) return false;
        if (PC(m0)+PC(m1)+PC(m2)+PC(m3) < 11) return false;
        byte[] inp=new byte[24];
        Array.Copy(b,o,inp,0,16); Array.Copy(SUF,0,inp,16,8);
        byte[] pk=md5.ComputeHash(inp);
        AES.Key=pk;
        using (var d=AES.CreateDecryptor()){
            byte[] pt=d.TransformFinalBlock(CIPHER,0,16);
            for(int j=0;j<8;j++) if((pt[j]^IV[j])!=FRAG[j]) return false;
            return true;
        }
    }

    public static List<string> Run(int pid, byte[] frag, byte[] cipher, byte[] iv, out long mb) {
        FRAG=frag; CIPHER=cipher; IV=iv;
        SUF=new byte[]{1,0,0,0,0x73,0x41,0x6c,0x54};
        AES=Aes.Create(); AES.Mode=CipherMode.ECB; AES.Padding=PaddingMode.None;
        var found=new List<string>(); mb=0;
        IntPtr h=OpenProcess(0x0010|0x0400, false, pid);   // VM_READ | QUERY_INFORMATION
        if (h==IntPtr.Zero) throw new Exception("OpenProcess "+pid+" failed err="+Marshal.GetLastWin32Error());
        IntPtr addr=IntPtr.Zero; MBI mbi; uint sz=(uint)Marshal.SizeOf(typeof(MBI));
        long scanned=0;
        while (VirtualQueryEx(h, addr, out mbi, sz)!=0) {
            ulong baseA=(ulong)mbi.BaseAddress.ToInt64();
            ulong size=(ulong)mbi.RegionSize.ToInt64();
            bool ok = mbi.State==MEM_COMMIT && mbi.Type==MEM_PRIVATE
                      && (mbi.Protect==PAGE_RW || mbi.Protect==PAGE_WC)
                      && (mbi.Protect & (PAGE_GUARD|PAGE_NOACCESS))==0;
            if (ok && size>0 && size<0x40000000UL) {
                try {
                    byte[] buf=new byte[size]; IntPtr rd;
                    if (ReadProcessMemory(h, mbi.BaseAddress, buf, (IntPtr)size, out rd)) {
                        int n=(int)rd; scanned+=n;
                        for (int o=0; o+16<=n; o+=8) {
                            if (Hit(buf,o)) {
                                var sb=new System.Text.StringBuilder();
                                for(int j=0;j<16;j++) sb.Append(buf[o+j].ToString("x2"));
                                string hex=sb.ToString();
                                if(!found.Contains(hex)) found.Add(hex);
                                if(found.Count>=6){ CloseHandle(h); mb=scanned/1048576; return found; }
                            }
                        }
                    }
                } catch {}
            }
            ulong next=baseA+size; if(next<=baseA) break;
            addr=(IntPtr)(long)next; if(next>0x7FFFFFFFFFFFUL) break;
        }
        CloseHandle(h); mb=scanned/1048576; return found;
    }
}
'@
Add-Type -TypeDefinition $cs -Language CSharp

[KeyScan]::EnableDebug()

# 动态读当前 message.db 页1 算校验靶(FRAG/CIPHER), 避免硬编码过期
$mdb = $null
foreach ($ud in (Get-ChildItem "C:\Users" -Directory -ErrorAction SilentlyContinue)) {
    $wx = Join-Path $ud.FullName "Documents\WXWork"
    if (-not (Test-Path $wx)) { continue }
    foreach ($f in (Get-ChildItem $wx -Filter message.db -Recurse -Depth 3 -ErrorAction SilentlyContinue)) {
        if ($f.FullName -match "\\Backup\\") { continue }
        if (-not $mdb -or $f.Length -gt (Get-Item $mdb).Length) { $mdb = $f.FullName }
    }
}
if (-not $mdb) { "NO_MESSAGE_DB"; exit }
$h = New-Object byte[] 96
$fsr = [System.IO.File]::Open($mdb,"Open","Read","ReadWrite"); $fsr.Read($h,0,96) | Out-Null; $fsr.Close()
$FRAG   = $h[16..23]
$CIPHER = $h[8..15] + $h[24..31]
$IV     = [byte[]](0x20,0xd7,0x42,0x0f,0x9c,0x37,0xa3,0x5d,0xca,0x6f,0xe9,0x2a,0x1c,0x69,0x99,0xa9)

$procs = Get-Process -Name WXWork -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending
if (-not $procs) { "NO_WXWORK_PROCESS"; exit }
"WXWork 进程: " + (($procs | ForEach-Object { "$($_.Id)($([math]::Round($_.WorkingSet64/1MB))MB)" }) -join ' ')

$all = @()
foreach ($p in $procs) {
    $mb = 0
    try { $keys = [KeyScan]::Run($p.Id, $FRAG, $CIPHER, $IV, [ref]$mb) }
    catch { "PID $($p.Id) 失败: $($_.Exception.Message)"; continue }
    "PID $($p.Id): 扫 ${mb}MB, 命中 $($keys.Count)"
    $all += $keys
    if ($keys.Count -gt 0) { break }   # 找到就停
}
$all = $all | Select-Object -Unique
if ($all.Count -gt 0) {
    "FOUND_KEYS:"
    $all | ForEach-Object { "KEY=$_" }
} else {
    "NO_KEY_FOUND"
}
