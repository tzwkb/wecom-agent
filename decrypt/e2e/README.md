# wecom-agent 解密模块 测试

## 文件
| 文件 | 作用 |
|---|---|
| `test_e2e.py` | 端到端测试(双端: macOS `wecom_local` / Windows `wecom_win`, 9 cmd + `--json`) |
| `check_consistency.py` | 架构一致性校验(skills↔langlobal 同步 + wechat↔wecom vendored 一致) |

> Windows 另有一键自测 `decrypt/windows/run_test.ps1`(12 项)。

## 跑法
```bash
python3 decrypt/e2e/test_e2e.py            # 端到端 9 项
python3 decrypt/e2e/test_e2e.py --full     # + media 导出
python3 decrypt/e2e/check_consistency.py   # 一致性校验
```
退出码 0=全过 / 1=有失败。

## 端到端前提(不满足必挂)
先提 key + 解密:
- **macOS**: `decrypt/macos/read_wecom.py`(企微登录 + adhoc 重签)
- **Windows**: `decrypt/windows/run.ps1`(一键)

## 改代码后 —— 确保一致性三步
```
改代码 → check_consistency.py(查漂移) → test_e2e.py(查功能) → 都绿才 commit
```
跨项目总指南见 `Langlobal/decrypt-shared/TESTING.md`;架构目标骨架见 `Langlobal/decrypt-shared/decrypt-modules-alignment.md`。
