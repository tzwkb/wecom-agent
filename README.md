# wecom-agent — 企业微信 agent 接入 skill

让任意 agent（Claude Code / 其他）通过自建应用 API 直连企业微信，发消息、查通讯录、调任意官方接口。**不限企业规模，无扫码，无 90 天续期，命令不过第三方服务器。**

## 一次性配置（管理员做）

### 1. 建自建应用，拿三个凭证

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin) → **应用管理** → **自建** → **创建应用**
2. 进应用详情页，记下：
   - **AgentId**（应用 ID）
   - **Secret**（点「查看」，会推送到你的企业微信）
3. **我的企业** → **企业信息**，底部记下 **企业ID（CorpID）**

### 2. 开权限（按需）

应用详情页 → 配置以下能力：

| 你要做的事 | 需要开的权限 |
|---|---|
| 发消息给成员 | 默认就有（应用可见范围内） |
| 读通讯录/成员 | **通讯录同步** 或 在应用「通讯录」权限里勾选可见范围 |
| 文档/日程/会议 | 对应的接口权限 |

> ⚠️ 通讯录读取受企微隐私策略限制：需在应用可见范围内，且开启通讯录权限。否则返回 `60011`/`48002`。

### 3. 配置 IP 白名单

应用详情页 → **企业可信IP** → 填入运行 agent 的服务器公网 IP。否则调 API 返回 `60020`。

### 4. 填凭证

```bash
cp config.example.json config.json
# 编辑 config.json 填入 corpid / secret / agentid
```

或用环境变量：
```bash
export WECOM_CORPID=xxx WECOM_SECRET=xxx WECOM_AGENTID=xxx
```

## 验证

```bash
python3 wecom.py contact list_departments
# 成功返回部门列表；token 自动获取并缓存到 .token_cache.json（2h）
```

## 分发给同事

打包整个 `wecom-agent/` 目录发给同事。**删掉 `config.json` 和 `.token_cache.json`**（含密钥）。同一企业同事可共用一套凭证，也可各自填。

零依赖（仅 Python 3 标准库），无需 pip install。

## 命令参考

见 [SKILL.md](SKILL.md)。技术同事可用「逃生舱」`call` 直调任意官方 API，不受封装范围限制。

## 安全

- `config.json`、`.token_cache.json`、`all_keys*` 已在 `.gitignore`
- token 缓存文件权限 `600`
- 发消息、改日程等写操作建议在 agent 侧加确认
