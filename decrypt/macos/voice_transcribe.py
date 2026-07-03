#!/usr/bin/env python3
"""企业微信(macOS)语音消息转文字 —— 仅**本地缓存**的 SILK 语音(已播放/已下载)。

来源: Caches/Voices/**/*.dat (SILK v3, 首字节 0x02 是微信前缀)。
流程: 剥 0x02 → pilk SILK→PCM → ffmpeg PCM→wav → mlx-whisper(large-v3) 转写。
输出: decrypt/macos/export/voice_transcripts.json (含 file/时间/时长/text)。
依赖: pip install pilk mlx-whisper; ffmpeg; Apple Silicon(mlx)。
覆盖: 仅本地缓存(实测约 6/231 条)；未缓存的需联网 CDN，本脚本不做。
用法: voice_transcribe.py [--model REPO] [--lang zh]
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wecom_paths import caches
VOICES = os.path.join(caches(), "Voices")
OUT = os.path.join(HERE, "export", "voice_transcripts.json")
MODEL = "mlx-community/whisper-large-v3-mlx"
LANG = "zh"


def _need(mod, pip=None):
    try:
        return __import__(mod)
    except ImportError:
        sys.exit(f"缺依赖 {mod} → pip install {pip or mod}")


def main():
    global MODEL, LANG
    if "--model" in sys.argv:
        MODEL = sys.argv[sys.argv.index("--model") + 1]
    if "--lang" in sys.argv:
        LANG = sys.argv[sys.argv.index("--lang") + 1]
    pilk = _need("pilk")
    mlx_whisper = _need("mlx_whisper", "mlx-whisper")

    dats = sorted(glob.glob(os.path.join(VOICES, "**", "*.dat"), recursive=True))
    silks = []
    for d in dats:
        try:
            with open(d, "rb") as f:
                if b"SILK" in f.read(16):
                    silks.append(d)
        except OSError:
            pass
    print(f"本地缓存语音: {len(silks)} 条 SILK; 模型 {MODEL} (首次会下载~3GB)")
    if not silks:
        sys.exit("无缓存语音 .dat")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = tempfile.mkdtemp()
    results = []
    for i, d in enumerate(silks, 1):
        try:
            raw = open(d, "rb").read()
            if raw[:1] == b"\x02":          # 剥微信 SILK 前缀
                raw = raw[1:]
            silk = os.path.join(tmp, f"{i}.silk")
            with open(silk, "wb") as f:
                f.write(raw)
            pcm = os.path.join(tmp, f"{i}.pcm")
            dur = pilk.decode(silk, pcm, pcm_rate=24000)   # SILK→PCM, 返回时长(秒)
            wav = os.path.join(tmp, f"{i}.wav")
            subprocess.run(["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1",
                            "-i", pcm, wav], capture_output=True)
            r = mlx_whisper.transcribe(wav, path_or_hf_repo=MODEL, language=LANG)
            text = (r.get("text") or "").strip()
            results.append({
                "file": os.path.basename(d),
                "path": d,
                "mtime": int(os.path.getmtime(d)),
                "duration": round(float(dur), 1),
                "text": text,
            })
            print(f"  [{i}/{len(silks)}] {round(float(dur),1)}s: {text[:60]}")
        except Exception as e:
            print(f"  [{i}/{len(silks)}] 失败: {e}")

    json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=2)
    try:
        os.chmod(OUT, 0o600)
    except OSError:
        pass
    print(f"\n✅ 转写 {len(results)} 条 → {OUT}")
    print("注: 仅本地缓存语音; 想覆盖全部需另做 CDN 下载(fileid+aeskey 在消息 DER)。")


if __name__ == "__main__":
    main()
