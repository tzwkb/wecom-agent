---
name: wecom-agent
description: 企业微信全能 agent——本地解密读取聊天记录、自建应用API发消息/查通讯录/读写在线文档/日程会议、实时接收消息并自主处理(自动回复/写文档)。触发词：企业微信/企微/wecom，读消息/导出聊天记录、发消息/通知、查通讯录/找人、建文档/读文档/编辑文档、日程/会议、实时接收/自动回复。
allowed-tools: Bash
---

# wecom-agent — 企业微信全能 agent

| 线 | 能力 | 入口 | 依赖 |
|---|---|---|---|
| **A 主动操作** | 发消息/通讯录/文档读写/日程/会议 | `wecom.py` | CorpID+Secret+AgentId + 可信IP |
| **B 本地读取** | 解密导出聊天记录(会话/发送者/时间/正文) | `decrypt/` | 企微登录 + adhoc 重签(去 hardened runtime) |
| **C 实时接收+自主处理** | 收消息→分析→自动回复/写文档 | `recv_server.py`+`agent_worker.py` | A 的凭证 + 接收Token/AESKey + 公网URL |

配置见 `README.md` 与 `docs/自建应用配置教程.md`。凭证写 `config.json`(已 gitignore)。

## A 主动操作（官方 API）

```bash
python3 wecom.py <category> <method> '<json参数>'   # 输出JSON, errcode:0 成功
```

| category | method | 参数 | 作用 |
|---|---|---|---|
| `contact` | `departments` | 无 | 部门列表(名称+ID) |
| `contact` | `users` | `{"department_id":1}` | 部门成员(userid+姓名) |
| `contact` | `get`/`search`/`list_id` | `{"userid"/"keyword":..}` | 成员详情/按名找人/成员ID列表 |
| `message` | `text`/`markdown`/`news` | `{"touser":"x","content":".."}` | 发消息(`touser`缺省@all,多人`|`分隔) |
| `doc` | `create`/`get`/`edit`/`del`/`rename`/`sheet_get`/`sheet_edit` | 透传 body | 在线文档/表格 读写+编辑(edit=batch_update) |
| `schedule`/`meeting` | `add`/`create`/`list`.. | 透传 body | 日程/会议 |
| `call` | 逃生舱 | `{"path":"/cgi-bin/..","body":{}}` | 任意官方接口 |

**写操作（发消息/删日程/改文档）执行前先向用户确认内容。**

## B 本地读取聊天记录（macOS，已验证）

前提：企业微信运行并登录 + 已对企微 adhoc 重签（见 `docs/解密思路.md`、[[wechat_codesign_pitfall]]）。

```bash
python3 decrypt/read_wecom.py        # ★一键: key有效则跳过扫描 → 解密 → 导出
# 或分步:
python3 decrypt/find_key_fast.py     # ① 活进程内存扫 16B key(只读,不注入); 存 wxwork_keys.json
python3 decrypt/decrypt_wxwork.py    # ② 全库解密(53个) → decrypt/decrypted/
python3 decrypt/export_wxwork.py     # ③ 结构化导出 → decrypt/export/messages.csv|json
python3 decrypt/monitor.py --once    # 增量: 用已存key重解密取新消息(--poll N 持续监控)
```

解析已覆盖：发送者真名(Session.db USER)、会话名、消息类型——文本 / 图片 / `[语音]` / `[文件]名` / `[文档]标题+链接` / `[卡片]标题+链接` / 系统 / 会议。
可选语音转写：`voice_transcribe.py`（本地缓存 SILK→whisper，需 pilk+mlx-whisper，仅覆盖已播放的）。
key 存盘后 ②③与 monitor **无需再扫内存**。离线兜底 `find_key_offline.py`。方案见 `docs/解密思路.md`。产物私密、已 gitignore。

**本地数据查询/分析**（解密后，全本地无网络）：`python3 decrypt/wecom_local.py <子命令>`

| 子命令 | 作用 |
|---|---|
| `contacts [词]` | 通讯录 138 人（姓名/部门/职位/手机/邮箱），可按词查 |
| `conversations` | 会话列表（名称/消息数/最后时间） |
| `members <会话>` | 群成员（按发言数） |
| `search <词>` | 全文搜索消息 |
| `stats` | 统计画像（发言排行/会话排行/类型/按小时/按天） |
| `todo` / `calendar` | 本地待办 / 日程 |
| `media [--out]` | 导出明文缓存图片+文件（161图+119文件） |

语音转写：`python3 decrypt/voice_transcribe.py`（缓存 SILK→whisper large-v3，已验证 6 条）。

## C 实时接收 + 自主处理

```bash
# 1. 按 docs/自建应用配置教程.md 配「接收消息」(URL/Token/EncodingAESKey)
# 2. 公网暴露: cloudflared tunnel --url http://localhost:8000
python3 recv_server.py               # 验签+AES解密+快速ACK+入队 jobs/inbox.jsonl
python3 agent_worker.py              # 读队列→决策→经wecom.py回复/写文档
```

`config.json` 配 `llm_base_url/llm_key/llm_model`(OpenAI 兼容) → LLM 自主决策；`"auto_reply":false` 仅记录不发（人工把关）。

## Agent 触发规则

| 用户说 | 调用 |
|---|---|
| "导出/读我的企微聊天" | B 线三步 |
| "发企微给X""通知X" | `message text` |
| "查通讯录""找叫X的人" | `contact users/search` |
| "建/读企微文档" | `doc create/get` |
| "约会议""建日程" | `meeting create`/`schedule add` |
| "让agent自动回复企微" | C 线(recv_server + agent_worker) |
| 封装没有的接口 | `call` |

## 状态

- **B 本地读取**：✅ 已实跑验证（5458 条结构化消息）。
- **A 主动操作**：代码就绪、端点按官方文档校正；待真实凭证联调（`gettoken` 已实测可达）。
- **C 实时接收+自主处理**：回调加解密、决策闭环均自测通过；待凭证+公网URL联调。
- 通讯录读取受企微隐私策略限制（需可见范围+权限，否则 `60011`/`60020`）。
