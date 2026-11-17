# -*- coding: utf-8 -*-
"""
一次性转换脚本：把「七班杀官网.html」（单文件内嵌 base64 截图 + APK）拆成
GitHub Pages 可直接托管的静态结构。

    七班杀官网.html  ->  index.html
                     ->  assets/img/*.jpg
                     ->  download/七班杀-v1.3.5.apk

生成后的 index.html 就是站点源文件，后续直接在它上面改，不要重复运行本脚本
（重复运行会用旧版覆盖掉手改内容）。

用法：
    python tools/extract_assets.py
"""

import base64
import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "七班杀官网.html")
OUT_HTML = os.path.join(ROOT, "index.html")
IMG_DIR = os.path.join(ROOT, "assets", "img")
DL_DIR = os.path.join(ROOT, "download")

APK_NAME = "七班杀-v1.3.5.apk"
APK_BYTES = 2239381
APK_SHA256 = "52fb7f0adad75e887bcce33d597a0319fd96ca1bae2daaa1863b7180582ef1e1"

# 截图按在源文件里出现的先后顺序命名，与页面文案（更新日志 / 首页 / 选将 / 原始手稿）对应
IMG_NAMES = ["hero-ui", "log", "home", "select", "manuscript"]


def fail(msg: str) -> None:
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    with open(SRC, "r", encoding="utf-8", errors="strict") as f:
        html = f.read()

    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(DL_DIR, exist_ok=True)

    # ---------- 1. 截图 ----------
    pattern = re.compile(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)")
    tokens = pattern.findall(html)
    if len(tokens) != len(IMG_NAMES):
        fail("预期 %d 张内嵌 JPEG，实际找到 %d 张" % (len(IMG_NAMES), len(tokens)))

    for idx, (b64, name) in enumerate(zip(tokens, IMG_NAMES)):
        raw = base64.b64decode(b64, validate=True)
        try:
            from PIL import Image  # 只为拿宽高，缺失时跳过
            w, h = Image.open(io.BytesIO(raw)).size
        except Exception:
            w = h = 0
        path = os.path.join(IMG_DIR, name + ".jpg")
        with open(path, "wb") as f:
            f.write(raw)
        rel = "assets/img/%s.jpg" % name
        # 只在第一次出现处替换，保证一一对应
        html = html.replace("data:image/jpeg;base64," + b64, rel, 1)
        # 顺手补上宽高与懒加载，避免首屏抖动
        if w and h:
            html = html.replace(
                '<img src="%s"' % rel,
                '<img src="%s" width="%d" height="%d" decoding="async"' % (rel, w, h),
                1,
            )
        else:
            html = html.replace('<img src="%s"' % rel, '<img src="%s" decoding="async"' % rel, 1)
        print("img  %-12s %7d bytes  %sx%s" % (name, len(raw), w, h))

    if "data:image/jpeg;base64" in html:
        fail("仍有未替换的内嵌 JPEG")

    # ---------- 2. APK ----------
    m = re.search(r'<script type="text/plain" id="apk-b64">([^<]+)</script>', html)
    if not m:
        fail("没有找到内嵌的 apk-b64 数据块")
    raw = base64.b64decode(re.sub(r"\s+", "", m.group(1)), validate=True)
    if len(raw) != APK_BYTES:
        fail("APK 大小不符：%d != %d" % (len(raw), APK_BYTES))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != APK_SHA256:
        fail("APK SHA-256 不符：%s" % digest)

    apk_path = os.path.join(DL_DIR, APK_NAME)
    with open(apk_path, "wb") as f:
        f.write(raw)
    print("apk  %-12s %7d bytes  sha256 ok" % (APK_NAME, len(raw)))

    # 连同上面的注释一起去掉
    html = re.sub(
        r"<!-- APK 数据[^>]*-->\s*<script type=\"text/plain\" id=\"apk-b64\">[^<]+</script>\s*",
        "",
        html,
    )
    if 'id="apk-b64"' in html:
        fail("apk-b64 数据块没有被完全移除")

    with open(OUT_HTML, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("html %-12s %7d bytes" % ("index.html", os.path.getsize(OUT_HTML)))


if __name__ == "__main__":
    main()
