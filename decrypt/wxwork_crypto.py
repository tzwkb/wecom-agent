#!/usr/bin/env python3
"""企业微信(WeCom, macOS) Info.db/Session.db 等 wxSQLite3 AES-128-CBC 解密核心。

方案(实测 Info.db 头吻合):
  - 页 key = md5(raw_key[16B] + 页号<u32 LE> + b"sAlT")
  - IV     = SQLite3MultipleCiphers sqlite3mcGenerateInitialVector(页号) = md5(LCG 16B)
  - AES-128-CBC, 无 HMAC, reserve=0, 页大小 4096
  - 页1: 偏移0-15 为 AES(SQLite头) 的密文; 偏移8-15 实为"偏移16-23密文"的搬运;
         偏移16-23 是明文 SQLite 头片段(plaintext_header)。解密时先把 8-15 还原回 16-23。

算法移植自 ylytdeng/wechat-decrypt(wxwork_crypto.py); 改用 cryptography 库(本机无 pycryptodome)。
raw_key 必须 16 字节。运行本文件 = 离线自测(不碰企业微信)。
"""
import hashlib
import json
import os
import sqlite3
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PAGE_SZ = 4096
SQLITE_HDR = b"SQLite format 3\x00"
WXSQLITE3_SALT = b"sAlT"


def _aes_cbc_dec(key, iv, data):
    d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return d.update(data) + d.finalize()


def _aes_cbc_enc(key, iv, data):
    e = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return e.update(data) + e.finalize()


def _modmult(a, b, c, m, s):
    q = s // a
    s = b * (s - a * q) - c * q
    if s < 0:
        s += m
    return s


def generate_initial_vector(page_no):
    """对齐 SQLite3MultipleCiphers sqlite3mcGenerateInitialVector()。"""
    z = page_no + 1
    initkey = bytearray(16)
    for idx in range(4):
        z = _modmult(52774, 40692, 3791, 2147483399, z)
        initkey[idx * 4 : idx * 4 + 4] = struct.pack("<I", z & 0xFFFFFFFF)
    return hashlib.md5(initkey).digest()


def derive_page_key(raw_key, page_no):
    if len(raw_key) != 16:
        raise ValueError("raw key must be 16 bytes")
    return hashlib.md5(raw_key + struct.pack("<I", page_no) + WXSQLITE3_SALT).digest()


def has_plain_header_fragment(page):
    """新版 wxSQLite3 AES 模式在页1偏移16-23保留明文 SQLite 头片段。"""
    if len(page) < 24:
        return False
    h = page[16:24]
    page_size = (h[0] << 8) | h[1]
    if page_size == 1:
        page_size = 65536
    return (
        512 <= page_size <= 65536
        and (page_size & (page_size - 1)) == 0
        and h[5] == 0x40
        and h[6] == 0x20
        and h[7] == 0x20
    )


def quick_verify(raw_key, page1):
    """单块快速校验: 只解页1偏移16处第一个密文块, 看 decrypted[16:24] 是否==明文片段。
    每候选仅 1 次 md5 + 1 次 AES 块, 适合海量候选扫描。"""
    if len(raw_key) != 16 or len(page1) < 32 or not has_plain_header_fragment(page1):
        return False
    frag = bytes(page1[16:24])
    cipher_block0 = bytes(page1[8:16]) + bytes(page1[24:32])  # 还原后的 data[16:32]
    try:
        pt0 = _aes_cbc_dec(derive_page_key(raw_key, 1), generate_initial_vector(1), cipher_block0)
    except Exception:
        return False
    return pt0[:8] == frag


def decrypt_page(raw_key, page_data, page_no):
    if len(page_data) != PAGE_SZ:
        raise ValueError(f"page must be exactly {PAGE_SZ} bytes")
    data = bytearray(page_data)
    if page_no == 1 and has_plain_header_fragment(data):
        frag = bytes(data[16:24])
        data[16:24] = data[8:16]
        data[16:] = _aes_cbc_dec(
            derive_page_key(raw_key, 1), generate_initial_vector(1), bytes(data[16:])
        )
        if bytes(data[16:24]) != frag:
            raise ValueError("key validation failed")
        data[:16] = SQLITE_HDR
        return bytes(data)
    return _aes_cbc_dec(
        derive_page_key(raw_key, page_no), generate_initial_vector(page_no), bytes(data)
    )


def looks_like_page1(page):
    return (
        page[: len(SQLITE_HDR)] == SQLITE_HDR
        and len(page) >= 108
        and page[100] in (0x02, 0x05, 0x0A, 0x0D)
    )


def verify_key(raw_key, page1):
    """全量确认: 解整张页1并验证标准 SQLite 头 + b-tree 类型。用于 quick_verify 命中后排除误报。"""
    if len(raw_key) != 16 or len(page1) < PAGE_SZ:
        return False
    try:
        return looks_like_page1(decrypt_page(raw_key, page1[:PAGE_SZ], 1))
    except Exception:
        return False


def decrypt_database(db_path, out_path, raw_key):
    size = os.path.getsize(db_path)
    total_pages = (size + PAGE_SZ - 1) // PAGE_SZ
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(db_path, "rb") as fin, open(out_path, "wb") as fout:
        for page_no in range(1, total_pages + 1):
            page = fin.read(PAGE_SZ)
            if not page:
                break
            if len(page) < PAGE_SZ:
                page += b"\x00" * (PAGE_SZ - len(page))
            fout.write(decrypt_page(raw_key, page, page_no))


def table_names(path):
    conn = sqlite3.connect(path)
    try:
        return [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
    finally:
        conn.close()


def load_valid_keys(keys_json, page1=None):
    """从 wxwork_keys.json 读 16 字节 key; 传 page1 则只返回能解它的(去重)。
    供 decrypt/monitor/read_wecom 复用，避免各自重写"读key+hex+verify"循环。"""
    out = []
    if not os.path.exists(keys_json):
        return out
    try:
        data = json.load(open(keys_json))
    except (ValueError, OSError):
        return out
    for v in data.values():
        try:
            k = bytes.fromhex(v)
        except (ValueError, TypeError):
            continue
        if len(k) == 16 and k not in out and (page1 is None or verify_key(k, page1)):
            out.append(k)
    return out


# ── 离线自测(不碰企业微信; 用合成页验证算法移植正确) ────────────────────
def _encrypt_page1(raw_key, plain_page):
    data = bytearray(plain_page)
    db_header = bytes(data[16:24])
    pk, iv = derive_page_key(raw_key, 1), generate_initial_vector(1)
    data[:16] = _aes_cbc_enc(pk, iv, bytes(data[:16]))
    data[16:] = _aes_cbc_enc(pk, iv, bytes(data[16:]))
    data[8:16] = data[16:24]
    data[16:24] = db_header
    return bytes(data)


def _selftest():
    raw_key = bytes.fromhex("00112233445566778899aabbccddeeff")
    page = bytearray(PAGE_SZ)
    page[:16] = SQLITE_HDR
    page[16:24] = bytes.fromhex("1000020200402020")
    page[100] = 0x0D
    enc = _encrypt_page1(raw_key, bytes(page))
    assert has_plain_header_fragment(enc), "header fragment 检测失败"
    assert quick_verify(raw_key, enc), "quick_verify 失败"
    assert verify_key(raw_key, enc), "verify_key 失败"
    assert not verify_key(os.urandom(16), enc), "错误key误判为正确(假阳)"
    assert decrypt_page(raw_key, enc, 1) == bytes(page), "页1 roundtrip 不一致"
    print("self-test PASS: wxSQLite3 AES-128 算法移植正确, quick_verify/verify_key 工作正常")


if __name__ == "__main__":
    _selftest()
