# -*- coding: utf-8 -*-
"""上线前自检：确认 index.html 没有残留内嵌资源、没有死链、本地引用都存在。

    python tools/check-site.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
s = open(HTML, encoding="utf-8").read()
ok = True


def check(label, cond, detail=""):
    global ok
    print(("ok    " if cond else "FAIL  ") + label + ("  " + detail if detail else ""))
    if not cond:
        ok = False


size = os.path.getsize(HTML)
check("页面体积 < 200 KB", size < 200_000, "%d 字节" % size)
check("无 base64 图片残留", "data:image/jpeg" not in s)
check("无内嵌 APK 数据块", "apk-b64" not in s)
check("APK 直链（顶栏）", s.count("download/七班杀-v1.3.5.apk") >= 1,
      "%d 处" % s.count("download/七班杀-v1.3.5.apk"))
check("未依赖飞书 CDN", "feishu" not in s)
check("自托管字体引用", "assets/fonts/noto-serif-sc.woff2" in s and "assets/fonts/noto-sans-sc.woff2" in s)
check("无内联事件处理", not re.search(r"\son(click|load|error)=", s))

ld = re.search(r'<script type="application/ld\+json">(.+?)</script>', s, re.S)
try:
    json.loads(ld.group(1))
    check("JSON-LD 可解析", True)
except Exception as e:  # noqa: BLE001
    check("JSON-LD 可解析", False, str(e))

# 锚点：href="#x" 必须有对应 id
body = s[s.find("</head>"):]
ids = set(re.findall(r'id="([^"]+)"', body))
anchors = set(re.findall(r'href="#([^"]+)"', body))
check("页内锚点都指向存在的 id", not (anchors - ids), "缺失: %s" % sorted(anchors - ids))

# 小节与导航一致
sections = re.findall(r'<section class="sec" id="([a-z]+)"', s)
nav_links = re.findall(r'<nav class="nav-links"[\s\S]*?</nav>', s)[0]
nav_ids = set(re.findall(r'href="#([a-z]+)"', nav_links))
check("导航只指向现存小节", not (nav_ids - set(sections)), "导航 %s / 小节 %s" % (sorted(nav_ids), sections))

# 本地引用必须存在
local = sorted(set(re.findall(r'(?:href|src)="((?:assets|download)/[^"]+)"', s)))
for p in local:
    check("引用存在 %s" % p, os.path.exists(os.path.join(ROOT, p)))

for f in ("404.html", ".nojekyll", "assets/fonts/noto-serif-sc.woff2",
          "assets/fonts/noto-sans-sc.woff2", "download/七班杀-v1.3.5.apk"):
    check("文件存在 %s" % f, os.path.exists(os.path.join(ROOT, f)))

sys.exit(0 if ok else 1)
