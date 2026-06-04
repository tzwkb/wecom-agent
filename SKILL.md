---
name: wecom-agent
description: 用企业微信自建应用 API 操作企业微信——发消息/通知、查通讯录找人、建日程、约会议、读写文档。触发词：发企业微信、企微通知、查通讯录、企业微信找人、建日程、约会议、企微文档、wecom、企业微信发消息。
allowed-tools: Bash
---

# wecom-agent — 企业微信主动操作

通过自建应用官方 API 操作企业微信，直连、不限企业规模。驱动脚本 `wecom.py`（零依赖 Python3）。

> ⚠️ 本 skill 只做**主动操作**（发消息/通讯录/日程/会议/文档），**不读取人与人的聊天记录**（那是另一套会话存档/本地解密）。

## 配置（首次）

需 `CorpID` / `Secret` / `AgentId`（管理员在企微后台建自建应用获取，详见 README.md）。

```bash
cp config.example.json config.json   # 填三个值
# 或 export WECOM_CORPID=.. WECOM_SECRET=.. WECOM_AGENTID=..
```

验证：`python3 wecom.py contact departments` 返回部门列表即通。

## 调用格式

```bash
python3 wecom.py <category> <method> '<json参数>'
```

输出统一 JSON。`errcode:0` 为成功，非 0 查 `errmsg`。

## 命令速查

| category | method | 参数 | 作用 |
|---|---|---|---|
| `contact` | `departments` | 无 | 部门列表 |
| `contact` | `users` | `{"department_id":1}` | 部门成员 |
| `contact` | `get` | `{"userid":"x"}` | 成员详情 |
| `contact` | `search` | `{"keyword":"张"}` | 按姓名找人（本地过滤） |
| `message` | `text` | `{"touser":"x","content":".."}` | 发文本 |
| `message` | `markdown` | `{"touser":"x","content":".."}` | 发 markdown |
| `message` | `news` | `{"touser":"x","articles":[..]}` | 发图文卡片 |
| `schedule` | `add`/`get`/`del`/`list` | 透传 body | 日程 |
| `meeting` | `create`/`cancel`/`list`/`info` | 透传 body | 会议 |
| `doc` | `create`/`get`/`del` | 透传 body | 文档 |
| `call` | （逃生舱，见下） | | 任意官方接口 |

`touser` 缺省 `@all`；多人用 `|` 分隔（`"zhang|li"`）。

## 逃生舱 call（覆盖未封装的接口）

封装只含常用方法。任何官方接口都能用 `call` 直接打：

```bash
python3 wecom.py call POST /cgi-bin/任意路径 '{"path":"/cgi-bin/任意路径","body":{...}}'
python3 wecom.py call GET  /cgi-bin/任意路径 '{"path":"/cgi-bin/任意路径","params":{...}}'
```

token 自动注入。`schedule`/`meeting`/`doc` 的 body 字段结构以[官方文档](https://developer.work.weixin.qq.com/document/path/90664)为准。

## Agent 触发规则

| 用户说 | 调用 |
|---|---|
| "发企微给X" "通知X" | `message text` |
| "本地化部有谁" "查通讯录" | `contact users` / `departments` |
| "找叫X的人" "X的userid" | `contact search` / `get` |
| "建个日程" "约会议" | `schedule add` / `meeting create` |
| "建文档" "读文档X" | `doc create` / `get` |
| 封装没有的接口 | `call` |

**写操作**（发消息、删日程、改文档）执行前先向用户确认内容。

## 状态（开发中）

- `gettoken` 已实测可达；contact/message/schedule/meeting/doc 端点**待真实凭证联调验证**，联调后修正本表。
- 通讯录读取需应用开启通讯录权限 + 企业可信 IP 白名单，否则报 `60011`/`60020`。
