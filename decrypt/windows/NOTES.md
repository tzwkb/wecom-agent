# 企业微信 Windows 版移植 · 进展记录

## 环境
- UTM Win11 **ARM** VM，企业微信 **5.0.7**（x64 靠模拟跑），已登录真实工作号。
- SSH 自动化：`claude@192.168.x.x`（vmnet-shared 直连，非端口转发），私钥 `~/.ssh/utm_win`。
- 数据目录：`C:\Users\<user>\Documents\WXWork` + `AppData\Roaming\Tencent\WXWork`。

## Phase 0 侦察结论（2026-06-05）

77 个库 = **63 加密 + 14 明文辅助**（如 data_index.db 是明文 SQLite）。

### ★ 决定性：Windows 与 Mac 同一套加密（wxSQLite3 AES-128）

头部对照（前 24 字节 hex）：
```
Mac  Info.db    : a41d91375995d7d6 a97b64081cea10a7 1000020200402020
Win  message.db : 46f81f090bff137c e0a5c9b8d5fcac64 1000020200402020
```
结构一致：`[8B 按 key 变化的指纹][8B 密文][offset16 起 = 明文 SQLite 头]`
- offset16-17 `1000` = 页大小 4096
- offset20 `00` = **reserve 0**（SQLCipher 此处为 48 → 排除 SQLCipher）
- cipher_plaintext_header_size = **16**（前 16 字节加密，之后明文）
→ 与 Mac wxSQLite3 方案**完全相同**。

多把 key：加密库头部前 8 字节有 `46f8…/4f16…/7a91…` 数种 → 不同库组用不同 key（同 Mac）。
主消息库 `message.db` 5.4MB。

### 意味着
- `decrypt/wxwork_crypto.py`（Mac 解密核心）**可直接复用**，解密算法无需改写。
- 剩余移植工作：
  1. **key 提取** → 改 Windows：`OpenProcess` + `ReadProcessMemory` 扫 `WXWork.exe` 内存（替代 Mac 的 task_for_pid + mach_vm_read）；候选 key 校验复用 `wxwork_crypto.verify_key`。
  2. **路径** → Windows 版（Documents\WXWork 下各库）。
  3. **解密 + 解析** → 复用 `wxwork_crypto` + `export_wxwork`。
- Windows 无 task_for_pid 重签那套破事；ReadProcessMemory 只需管理员/同用户权限。

## Phase 1 实证打通（2026-06-05）★

**抓 key**：`windows/find_key.ps1`（PowerShell 内嵌 C#）扫 WXWork.exe 可写私有内存。
- 关键优化：**8 字节对齐扫描**（堆 key 必对齐，逐字节版烧 1426s CPU 仍没完）+ **复用 AES 对象**。优化后主进程(323MB)只扫 169MB 即命中。
- 抓到 key：`<16B key·本机抓取·不入库>`（16B）。
- 开了 SeDebugPrivilege；SSH(claude 管理员)能 OpenProcess 别用户(零九三号虚拟机)的 WXWork 进程。

**验证**：Mac `wxwork_crypto.quick_verify(key, page1)` = **True**；此 key 验证 **21 个库**（message/file/user/session/kv/company… 同指纹组）。多 key：calendar/crm 等另有 key 组。

**解密+读取**：Mac `decrypt_database` 原样解开 Windows `message.db`(11.6MB) → 合法 SQLite，29 表。
- `message_table` **14195 行真实消息**，列：`message_id, server_id, sequence, sender_id, conversation_id, content_type, send_time, flag, content, …`（结构≈Mac，列名略异）。
- content 是 protobuf（同 Mac），`export_wxwork.decode_text/render` 改列名即可解析。

→ **整条路打通：抓 key + 解密算法 + 读消息全部复用 Mac 代码**，零加密重写。

## 剩余（全是已知工程，无未知）
1. 抓全部 key 组（message 组已通；calendar/crm 等另抓）。
2. `find_key.ps1` 探路版 → 干净最终形态（PowerShell+C# 或装 Python 走 ctypes）。
3. 路径 + 列名适配 `export_wxwork`（conversation_id/sender_id… ≈ Mac）。
4. 打包 Windows skill。


## Phase 2 完成：补齐到 macOS 同级（2026-06-05）★

**名字解析 schema**：`user.db.user_table`(id→name/mobile/email) + `wechat_contactV1`(wxid→name) + `session.db.conversation_table`(id→name)；自己 uid = `S:a_b` 里最频繁那个；1:1 会话名取对方。

**新增**：
- `wecom_win.py` —— 全功能 CLI（子命令 `read/contacts/conversations/search/stats/todo`），复用 `wxwork_crypto`(解密) + `export_wxwork.decode_text/fmt_time`(解析原语)。
- `run.ps1` —— 一键入口：`find_key.ps1` 抓 key → `wecom_win` 跑子命令（对齐 macOS `read_wecom.py`）。
- `find_key.ps1` 修复：`$ErrorActionPreference` Stop→Continue（Stop 下递归搜库被 access-denied 终止，才是 NO_MESSAGE_DB 真因；glob 本身没问题）。

**实测全过（VM, 从零跑）**：`run.ps1` 自动抓 key(7580…) → `read` 14208 条带真名（`【张三】李四…`）；`contacts 余`→`张三|Sam|手机`；`stats` 发言/会话排行全真名（李四4531/王五/测试项目组…）；`search/conversations/todo` 均 OK。

**Windows 与 macOS 现已同级（核心读取/查询）。** 复用率：解密核心 100%、内容解析原语复用、仅"schema 绑定的胶水"按 Windows 表/列/库重写。

待补(非核心)：content_type 标签(现 `[类型N]`)、calendar/media/voice/openfile/monitor(不同库或 key)、key 缓存(免每次重扫)。

## Phase 3 完成：补齐全部二级功能 + 端到端 12/12（2026-06-05）★

新增子命令(全部实测)：**calendar**(calendar_r7.db 同 message key; 标题从 rawdata 提 CJK) / **media**(明文缓存 `Cache\{File,Image}` 导出 541 文件) / **openfile**(file.db 给发件人/时间 + `Cache\File` 按原名定位 → read_doc 解析 xlsx/pdf/docx/文本) / **voice**(定位 `Cache\Voice` 的 SILK; 转写需 faster-whisper) / **monitor**(水位增量) / **members**(session.db 群成员)。

依赖：`pycryptodome`(解密) + `openpyxl xlrd pypdf python-docx`(openfile)。坑：pdfplumber→pdfminer→cryptography 在 win-arm64 编译挂，改用纯 Python 的 **pypdf**(read_doc 自动回退)；lxml 有 win_arm64 wheel，python-docx 可用。

端到端：`run_test.ps1`(find_key→test_e2e.py 跑 12 命令→报告写桌面)，实测 **12/12 通过**。

**Windows 与 macOS 现已全功能对齐。**

## Phase 3.1 收尾打磨（2026-06-05）

- **content_type 标签**：Windows 码 ≠ Mac（图片 4/14/29、文件 15/16、文档 13、卡片 145/123/579…、通话 40/1018），覆盖 export_wxwork 的 MEDIA/CARD_TYPES/TYPE_LABEL 后复用其 `render()` → `[图片]/[文件]名/[卡片]标题/[文档]` 全出。
- **calendar 标题**：改用 `ex._pb_strings(rawdata)` 取干净 protobuf 字段、挑含 CJK 的 → “开发需求会议”（无尾巴杂字）。
- **voice 转写**：ARM VM 实测装不了——faster-whisper/ctranslate2/pilk 无 win_arm64 wheel，pywhispercpp 编译失败(无 C++ 工具链)。x64 Windows 有 wheel 可用，定位/导出不受影响。
- 整理：删 scp 手误乱码文件、清 .DS_Store、清 VM 探路脚本。

端到端复测：仍 **12/12**，报告在 VM 桌面。
