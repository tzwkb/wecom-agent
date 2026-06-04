# 企业微信 (macOS) 聊天记录解密 — 调查记录

环境: 企业微信 5.0.8 / macOS / Apple Silicon。frida 17.10.1 (系统 `/opt/homebrew/bin/python3`)。

## 已确认的架构事实（实测）

| 项 | 结论 |
|---|---|
| DB 引擎 | WCDB + **SQLCipher**(自带, 非系统 sqlite3) |
| 加密库 | **静态链接 OpenSSL**(满屏 EVP_*/AES_* 符号), 非 CommonCrypto |
| DB 文件头 | `a41d9137 5995d7d6`(8B 恒定 magic) + 8B 变化; 偏移16起 `1000 0202 00 40 20 20` = **明文SQLite头** → 用了 `cipher_plaintext_header_size` |
| 页大小 | 4096 (头偏移16-17=0x1000) |
| 主消息库 | `Profiles/<hash>/Messages1/Info.db`; 会话 `Session.db`; 通讯录 `roster.db` |
| 反调试 | **登录时检测 frida → 崩溃**。spawn 必杀; 登录中 attach 崩; **登录后 attach 稳定** |
| DB 页 key | **仅登录开库时设置一次**, 之后页缓存在内存; 运行时捕获不到 |
| 消息内容 | 另有逐条 AES-256-**GCM** 加密(EVP, IV末尾4字节0) |

## hardened runtime 与重签名（关键坎）

- 企业微信开 `flags=0x10000(runtime)` → frida 无法 attach。
- 必须 adhoc 重签名去掉。**坑**: `codesign --force --deep --sign -` 会清空 entitlements → 破坏登录(`RequestLoginKeys invalid`)。
- **正解**: 从原始 dmg 提取原始 entitlements, 重签时带上 + 加 `get-task-allow`:
  ```
  codesign -d --entitlements :- <原始app> > ent.plist
  # 加 com.apple.security.get-task-allow=true
  codesign --force --deep --sign - --entitlements ent.plist /Applications/企业微信.app
  ```
  关键 entitlement: `application-groups`(访问数据容器, 缺则登录崩)。
- 副作用: 重签后需重新扫码登录; 日常用建议重装恢复签名。

## 已验证可行的读取方法 ✅

**内存提取法**(无需 key、无需 frida、不触发反调试):
- 企业微信登录后, 解密的 SQLite 页缓存在进程内存。
- `task_for_pid`(ctypes, 需上面的重签名) 只读内存, 扫 `SQLite format 3` 头 / 消息文本。
- 实测: 精准搜索关键词可提取真实对话(与屏幕一致)。脚本 `extract_messages.py`(广度扫描,噪音多) / 定向搜索(干净)。
- 局限: 广度扫描混入 UI 模板串; 消息库页在 pager 缓存分散, 非连续, 难整库重建。

## 未通的路（已排除, 省得重走）

- spawn + 任意 hook → 反调试秒杀。
- 登录中 attach → 崩。
- hook CommonCrypto CCCrypt/CCKeyDerivationPBKDF → 抓到的是消息/缓存 key, 非 DB key(且 DB 走 OpenSSL 不走 CC)。
- hook EVP_DecryptInit/Update、AES_set_decrypt_key、AES_decrypt(登录后) → 全是消息 GCM key / 运行时缓存 key; **DB 页 key 一个没有**(登录时已设, 错过)。
- 捕获的所有 key(572 裸key + 151 EVP) 试解 Info.db(page2 b-tree 验证, 全 reserve/IV 方案) → **全 MISS**。
- 内存扫 DB salt 定位 codec → 0 命中(plaintext_header 下 salt 不在偏移0)。

## 干净全量解密的下一步（待建）

DB 页 key 只在登录设置, 登录拒 frida。**非 frida 注入**绕过:
1. **DYLD_INSERT_LIBRARIES 注入 dylib**(hardened runtime 已去, 可注入): 写 dylib hook `AES_set_decrypt_key`/`PKCS5_PBKDF2_HMAC`, 启动即在进程内, 反调试检测不到 frida 痕迹, 登录开库时抓 DB key。`open -a 企业微信 --env DYLD_INSERT_LIBRARIES=...`。
2. 拿到 key 后: SQLCipher AES-256-CBC + `cipher_plaintext_header_size` 参数解密 Info.db → 标准 sqlite3 → SELECT 消息。

## 脚本清单
- `hook_*.js` / `attach_*.py` — 各种 frida hook(探索用, 多数已证无效, 留作参考)
- `extract_messages.py` — ✅ 内存提取(可用)
- `carve_mem.py` / `carve_schema.py` — 内存扫解密SQLite页/schema
- `crack_page2.py` / `exhaustive.py` — key 试解(page2验证)
- `decrypt_db.py` — 拿到 key 后的整库解密(待 key)

## 2026-06-04 续: DYLD注入突破 + 消息库仍未破

### ✅ 重大突破: DYLD dylib注入(绕过反调试)
- WeCom开hardened runtime+sandbox+library validation。
- 解法: 重签名加 `get-task-allow`+`disable-library-validation`(基于dmg原始entitlements,保留app-groups), 然后 `open --env DYLD_INSERT_LIBRARIES=keyhook.dylib`。
- dylib构造函数做 ARM64 inline hook(前16字节非PC相对的函数: AES_set_decrypt_key/EVP_CipherInit_ex/EVP_DecryptUpdate 可hook; AES_cbc_encrypt不可;AES_decrypt可hook但破坏登录)。
- **沙盒坑**: dylib日志必须写容器内 `~/Library/Containers/com.tencent.WeWorkMac/Data/`, 写/tmp被沙盒拒(静默无日志)。
- 实测: 登录开库时抓到大量key, 无frida痕迹反调试不触发, WeCom正常登录。keyhook.c(v4)=最终版。

### 已破解的库
- **config/feature库**: key=ASCII `wework@tencent#123!feature_local`(256) 和 base64串key, **ECB模式**。DU hook抓到明文JSON `{"config":{"Devic...`。

### ❌ 消息库 Info.db 仍未破(卡点)
- 抓了961个唯一key(EVP_CipherInit_ex + AES_set_decrypt_key)。
- Info.db头: offset0-15随机, **offset16-23明文SQLite头(页4096,reserve=0!)**, offset24+加密。
- 全方案试解MISS: CBC(IV=zero/salt/页号/前块, start=0/16/24/32, reserve=0-80), ECB, 多validation(b-tree@100, 页数, 文本编码, page2)。
- **结论**: 消息库key不在961捕获里, 或用了非AES-CBC/ECB的特殊scheme/单块路径。
- 疑因: ①v3 dedup MAXSEEN=128 cap可能丢了第129+个key(Info.db的) ②消息库走AES_decrypt单块(hook它破坏登录) ③WeCom反复--deep重签+注入后**越来越不稳**(27s→6s退出, 疑代码完整性自检), 难live抓页。

### 下一步候选
1. 提高dedup cap到无限, 重抓(但需WeCom活到Info.db open)。
2. 重装WeCom→干净单二进制重签(非--deep,免破坏helper)→稳定后注入, hook EVP_DecryptUpdate抓Info.db页明文(out)直接重建。
3. AES_decrypt hook加线程安全+延迟激活(避开登录crypto), 抓单块DB页key。

### 资产
- keyhook.c/keyhook.dylib — DYLD注入hook(可用)
- /tmp/allkeys.txt — 961候选key
- extract_messages.py — 内存提取(已验证读到真实消息,降噪后可用)

## 2026-06-04 终: 注入稳定化 + 消息库静态crypto壁垒

### ✅ 关键突破: resign不用--deep → 稳定+auto-login
- `codesign --force --sign -`(不加--deep) + 原始entitlements + get-task-allow + disable-library-validation。
- **会话保留, auto-login正常, WeCom稳定**(注入下活30s+)。之前--deep破坏helper导致秒退。
- 重装: 从 ~/Downloads/WeCom_5.0.8.99856_Apple.dmg, cp后 `xattr -dr com.apple.quarantine`。
- "13s退出"真因=QR超时(无会话); 有会话auto-login则不超时。

### ✅ DYLD注入完全可用(keyhook.c v6/v7)
- hook EVP_DecryptUpdate/CRYPTO_cbc128_decrypt/aes_v8_cbc_encrypt + 匹配Info.db/Session.db页 → 全程dump=0。
- 加in-process carve线程(mach_vm_region扫自身rw内存找解密SQLite页): **成功carve 180页**, 但全是**CEF/系统SQLite**(cfurl_cache/alt_services/urls/certificates/NSColorSpace), **无WeCom消息页**。

### ❌ 消息库壁垒(根本原因, 实测确认)
1. **静态编译crypto**: 消息库解密不走任何导出的OpenSSL函数(EVP/AES_decrypt/aes_v8/CRYPTO_cbc128全hook过, dump=0)。WCDB用自己静态链接的AES, 无导出符号, 无法dlsym/hook。
2. **瞬时解密**: 消息库页解密后不留在标准SQLite pager缓存(carve只找到CEF的, 找不到WeCom消息页)。用完即弃。
3. **双层加密**: DB层(整库) + 消息层(每条AES-256-GCM, 即捕获的NID901 key)。
4. 1023捕获key × 全AES模式/IV/reserve/PBKDF2 × 强验证(CREATE TABLE) = 全MISS。

### 唯一验证可用: 内存字符串提取(extract_messages.py)
- 读到真实对话内容(屏幕原文一致), 但无结构(无sender/time/会话归属), 噪音多。
- 因消息明文经过UI渲染层内存, 可提取文本; 但非结构化DB。

### 未尝试(需二进制逆向, 超范围)
- 静态分析定位WCDB内部AES函数地址 → inline hook(无符号, 需IDA/Ghidra逆向)。
- hook静态sqlite3的sqlite3_column_text(无导出符号)。
- hook WCDB C++ getMessage API(需逆向符号)。
