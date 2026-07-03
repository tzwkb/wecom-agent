# WeCom Agent

[中文](README_ZH.md) | English


## Overview

 WeCom local-reading and official API operation Agent Skill for chat decryption, contact/session search, messaging, calendar meetings, and online documents.

## Key Capabilities

- Reads and analyzes local WeCom chat data.
- Uses self-built app APIs for messaging, contacts, calendar, and document operations.
- Keeps a local-agent workflow controlled directly by the user.

## Usage

 Configure local decryption, WeCom app parameters, and available APIs according to README/SKILL.md.

## Status

 This repository is maintained or used according to the current README notes.

## Notes

 Official API operations depend on trusted domains, IP settings, and application permissions.

## Command and Configuration Reference

The following code blocks are preserved from the primary README. Commands, paths, and configuration keys are not translated; adjust them for the actual environment.

```bash
python3 decrypt/read_wecom.py               # 一键: 扫key→解密→导出 → decrypt/export/messages.csv|json
python3 decrypt/wecom_local.py stats        # 统计画像(发言/会话排行、按小时/天)
python3 decrypt/wecom_local.py contacts 张  # 查通讯录(姓名/部门/职位/手机/邮箱)
python3 decrypt/wecom_local.py search 报价  # 全文搜索消息
python3 decrypt/wecom_local.py conversations|members <会话>|todo|calendar|media
python3 decrypt/monitor.py --poll 30        # 增量盯新消息
python3 decrypt/voice_transcribe.py         # 语音转文字(需 pilk + mlx-whisper)
```

```bash
cp config.example.json config.json   # 填凭证(已 gitignore)
python3 selfcheck.py                  # 联调自检(只读先行)
python3 wecom.py message text '{"touser":"x","content":"hi"}'
python3 wecom.py doc edit '{"docid":"..","requests":[..]}'
```

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

## Detailed Technical Notes

The primary README keeps the original technical details, history notes, full commands, and file layout. This file maintains the English version of the core documentation; consult the primary README code blocks and paths when exact commands are needed.
