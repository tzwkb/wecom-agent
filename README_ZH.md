# WeCom Agent

[English](README.md) | 中文


**Agent Skill** — 企业微信本地读取与官方 API 操作助手，支持聊天记录解密、通讯录/会话搜索、发消息、日程会议和在线文档流程。

**Agent Skill** — WeCom assistant for local chat decryption/search plus official API operations for messaging, contacts, calendar meetings, and online docs.

让本地 agent **读取、分析、(配置后)操作**企业微信。macOS 已验证。

## 能力

| 线 | 能力 | 状态 |
|---|---|---|
| **B 本地读取** | 解密导出聊天记录、增量监控、通讯录/会话/全文搜索/统计画像、语音转写、媒体导出 | ✅ 已可用 |
| **A 主动操作** | 发消息、查通讯录、读写编辑在线文档、日程/会议（官方 API） | ⏸️ 代码就绪，待企业可信域名+IP（见 `docs/IT配置请求.md`） |

> 实时接收回调（C）已弃：本地 agent 由用户直接指挥，无需绕企微回调。代码 `recv_server.py`/`agent_worker.py` 封存。

## 快速开始（B 本地读取）

前提：企业微信已登录 + 已对企微做 adhoc 重签（去 hardened runtime，见 `docs/解密思路.md`）。

```bash
python3 decrypt/read_wecom.py               # 一键: 扫key→解密→导出 → decrypt/export/messages.csv|json
python3 decrypt/wecom_local.py stats        # 统计画像(发言/会话排行、按小时/天)
python3 decrypt/wecom_local.py contacts 张  # 查通讯录(姓名/部门/职位/手机/邮箱)
python3 decrypt/wecom_local.py search 报价  # 全文搜索消息
python3 decrypt/wecom_local.py conversations|members <会话>|todo|calendar|media
python3 decrypt/monitor.py --poll 30        # 增量盯新消息
python3 decrypt/voice_transcribe.py         # 语音转文字(需 pilk + mlx-whisper)
```

key 首次需企微在跑、登录态（活进程内存扫 16B key，只读不注入）；之后存盘复用，无需再扫。

## A 主动操作（官方 API）

需管理员建自建应用拿 `CorpID/Secret/AgentId`（`docs/自建应用配置教程.md`）。企微对国内主体强制要求**可信域名(备案)+可信IP**，须 IT 配合（`docs/IT配置请求.md`）。

```bash
cp config.example.json config.json   # 填凭证(已 gitignore)
python3 selfcheck.py                  # 联调自检(只读先行)
python3 wecom.py message text '{"touser":"x","content":"hi"}'
python3 wecom.py doc edit '{"docid":"..","requests":[..]}'
```
命令速查见 `SKILL.md`。

## 结构

```
wecom.py                          A线 API CLI（contact/message/doc/schedule/meeting/call）
selfcheck.py                      A线 凭证联调自检
recv_server.py / agent_worker.py  实时接收(封存)
decrypt/                          B线 本地解密读取(核心)
  wxwork_crypto.py                wxSQLite3 AES-128-CBC 解密核心(+自测)
  wecom_paths.py                  profile 路径自动探测
  find_key_fast.py + validate.c   活进程内存扫 16B key(C 加速)
  find_key_offline.py             离线兜底找 key
  decrypt_wxwork.py               全库解密
  export_wxwork.py                结构化导出(真名/类型/卡片/文件/文档)
  monitor.py                      增量监控
  wecom_local.py                  本地查询(通讯录/会话/搜索/统计/待办/日程/媒体)
  voice_transcribe.py             缓存语音 SILK→whisper 转写
  read_wecom.py                   一键封装
  NOTES.md                        解密调查时间线
  legacy/                         废弃探索(旧 carve/frida/注入方案)
docs/                             解密思路 / 自建应用配置教程 / IT配置请求 / 开发计划
```

## 隐私与安全

- **仅读本人设备本人账号。** 解密产物（`decrypt/decrypted/`、`export/`、`jobs/`）、凭证 `config.json`、密钥 `wxwork_keys.json` 均 `.gitignore`，不入库。
- B 线需对企微 adhoc 重签（破坏性；日常使用建议重装恢复原签名）。
- 路径自动探测，不硬编码用户名/profile。
- 依赖：B 核心仅 `cryptography`；`find_key_fast` 首次自动用 `clang` 编译 `validate.c`（需 Xcode 命令行工具）。文档解析(`openfile`)可选 `openpyxl`/`pdfplumber`/`python-docx`/`xlrd`；语音 `pilk`+`mlx-whisper`（Apple Silicon）。缺可选库自动降级提示。

## 原理

消息库 = wxSQLite3 AES-128-CBC（非 SQLCipher）。key 仅在登录后进程内存，读出后离线解密。详见 [`docs/解密思路.md`](docs/解密思路.md)。
