# -*- coding: utf-8 -*-
"""
把整包中文字体裁剪成只含本站用到的字形，输出 woff2。

字体取自 Google Fonts 官方的 Noto Serif SC / Noto Sans SC 可变字体（OFL 授权），
先实例化出静态字重，再按 index.html 的字符集裁剪，体积从 25 MB 量级降到 1 MB 以内。
字重返回到页面原有的表现（正文 400 + 大标题由浏览器加粗），与改造前一致。

用法：
    python tools/subset-fonts.py            # 字符集取自 index.html
    python tools/subset-fonts.py --refresh  # 重新下载源字体

依赖：fonttools、brotli（pip install fonttools brotli）
"""

import argparse
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
CACHE = os.path.join(ROOT, "tools", ".cache")

FONTS = [
    # 输出文件名, 源可变字体 URL, 实例化字重
    ("noto-serif-sc.woff2", "NotoSerifSC-VF.ttf",
     "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
     400),
    ("noto-sans-sc.woff2", "NotoSansSC-VF.ttf",
     "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
     400),
]

# 页面正文之外，字符集里再补一点将来改文案时常用到的符号与字母数字
EXTRA = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    " .,:;!?()[]{}<>/\\|-—–…·、，。：；？！（）【】《》“”‘’「」"
    "￥$@#%&*+=_~^♠♥♦♣★☆①②③④⑤⑥⑦⑧⑨⑩"
    "七班杀江西师大附中师生对决更新日志首页选将原始手稿下载安装说明制作"
)


def download(url: str, path: str) -> None:
    if os.path.exists(path) and os.path.getsize(path) > 5 * 1024 * 1024:
        return
    print("downloading %s ..." % os.path.basename(path))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        f.write(r.read())


def instance(vf_path: str, weight: int) -> str:
    """从可变字体实例化出某一静态字重，返回缓存文件路径。"""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    out = vf_path.replace("-VF.ttf", "-%d.ttf" % weight)
    if os.path.exists(out) and os.path.getsize(out) > 1024 * 1024:
        return out
    font = TTFont(vf_path)
    instantiateVariableFont(font, {"wght": weight}, inplace=True, updateFontNames=True)
    font.save(out)
    return out


def charset() -> str:
    with open(HTML, "r", encoding="utf-8") as f:
        html = f.read()
    return "".join(sorted(set(html) | set(EXTRA)))


def subset(src: str, out: str, text_file: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "fontTools.subset", src,
         "--text-file=%s" % text_file,
         "--flavor=woff2",
         "--layout-features=kern",
         "--hinting",
         "--output-file=%s" % out],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="重新下载源字体")
    args = ap.parse_args()

    os.makedirs(FONT_DIR, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)

    text = charset()
    tmp = os.path.join(CACHE, "charset.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    print("charset: %d 个字符" % len(text))

    for out_name, cache_name, url, weight in FONTS:
        vf = os.path.join(CACHE, cache_name)
        if args.refresh and os.path.exists(vf):
            os.remove(vf)
        download(url, vf)
        static = instance(vf, weight)
        out = os.path.join(FONT_DIR, out_name)
        subset(static, out, tmp)
        print("font   %-22s %8d bytes" % (out_name, os.path.getsize(out)))


if __name__ == "__main__":
    main()
