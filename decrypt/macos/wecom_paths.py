"""企业微信(macOS) 路径自动探测 —— 不硬编码用户名/profile，开箱即用、可分发。

profile 目录名是每账号一串 hash；本模块自动在沙盒容器里找含 Messages1 的那个
(可用环境变量 WECOM_PROFILE 指定)。
"""
import functools
import glob
import os

CONTAINER = os.path.expanduser("~/Library/Containers/com.tencent.WeWorkMac/Data")
_PROFILES = os.path.join(CONTAINER, "Documents", "Profiles")
_HERE = os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(maxsize=1)
def profile_dir():
    env = os.environ.get("WECOM_PROFILE")
    if env:
        p = env if os.path.isdir(env) else os.path.join(_PROFILES, env)
        if os.path.isdir(p):
            return p
    cands = [
        d for d in glob.glob(os.path.join(_PROFILES, "*"))
        if os.path.isdir(d) and os.path.isdir(os.path.join(d, "Messages1"))
    ]
    if not cands:
        raise SystemExit(f"未找到企业微信 profile (在 {_PROFILES})；企微是否登录过？")
    return max(cands, key=os.path.getmtime)   # 多账号取最近活跃


def info_db():
    return os.path.join(profile_dir(), "Messages1", "Info.db")


def session_db():
    return os.path.join(profile_dir(), "Messages1", "Session.db")


def caches():
    return os.path.join(profile_dir(), "Caches")


def decrypted(*parts):
    """解密输出树 decrypt/macos/decrypted/ 下的路径。"""
    return os.path.join(_HERE, "decrypted", *parts)
