#!/usr/bin/env python3
"""生成下载页：public/download/index.html（中文）和 public/en/download/index.html（英文）。

数据来自 data/release.json。发布新版本时只改这个文件（以后由发布流程自动改），再运行本脚本。
网站的内容安全策略不允许脚本，所以下载页是生成好的静态页面。

用法：
  python3 tools/build_download.py           # 生成
  python3 tools/build_download.py --check   # 只检查已提交的页面和数据是否一致（CI 用）
只用标准库。
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "release.json"
OUT = {"zh": ROOT / "public" / "download" / "index.html", "en": ROOT / "public" / "en" / "download" / "index.html"}
HASH = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ASSET = re.compile(r"^[A-Za-z0-9._-]+$")

e = html.escape

T = {
    "zh": {
        "lang": "zh-CN", "path": "/download/", "other": "/en/download/", "other_lang": "en", "other_label": "English",
        "title": "下载群星桌面端 · 群星 Qunxing",
        "desc": "下载群星桌面端：Windows 安装包，或免安装的完整应用包。用你已有的 AI 订阅探索开放数学问题，结果用 Lean 检验。",
        "home": "首页", "lang_nav": "语言", "sp": "", "bank": "题库", "bank_path": "/problems/", "h1": "下载群星桌面端",
        "lead": "在自己的电脑上，用你已有的 AI 订阅探索开放数学问题；结果用 Lean 检验。",
        "btn_setup": "下载 Windows 版（安装包）", "btn_zip": "完整应用包（免安装 zip）",
        "meta": "版本 {v} · {d} · 安装包 {s}", "zip_size": "{s}",
        "mirror": "下载慢？用国内镜像：", "mirror_setup": "安装包", "mirror_zip": "完整应用包",
        "notes": "版本说明", "verify_link": "核对文件", "mac": "目前只有 Windows 版，macOS 版在做。",
        "soon": "测试版还没发布。第一个版本发出后，这里会放下载按钮。",
        "soon_watch": "想第一时间知道：在 GitHub 打开 {repo}，点「Watch → Custom → Releases」。",
        "steps_h": "三步上手",
        "steps": [
            "<b>安装。</b>运行安装包，不需要管理员权限；或者把完整应用包解压到任意文件夹，双击 <code>Qunxing.exe</code>。",
            "<b>第一次打开。</b>新手引导会带你选好工作文件夹，找到电脑上已经装好的 Codex CLI、Claude Code 或 Gemini CLI，并连上一个当指挥台。用你已有的订阅或 API 都行。",
            "<b>抽一道题，开跑。</b>从题库抽一道开放问题，先查新，再让 AI 解题。随时可以暂停、追加预算、插话。Lean 核对和题意复核都通过的结果，会在星图上点亮。",
        ],
        "req_h": "需要什么",
        "req": [
            "Windows 10 或 11，64 位。",
            "至少一个会写代码的 AI 工具，并且已经登录：Codex CLI、Claude Code 或 Gemini CLI。",
            "Lean 4 是可选的：要让结果过 Lean 核对才需要，新手引导里会教怎么装。",
            "联网：抽题、更新题库、查新和调用 AI 时要联网。也可以设成只在本机运行。",
        ],
        "priv_h": "隐私",
        "priv": [
            "默认不上传任何东西。运行记录、证明和花费都留在你的电脑上。",
            "想把结果提交到群星，要你自己点「上传到群星」：分两步，每步单独同意。",
        ],
        "safe_h": "安全提示",
        "smartscreen": "如果 Windows 提示「Windows 已保护你的电脑」：这是因为程序还没有代码签名。确认文件是从本页或 GitHub 下载的，点「更多信息」，再点「仍要运行」。",
        "signed": "安装包和程序都有代码签名，发布者是群星项目。",
        "verify": "核对文件：在下载文件夹里打开 PowerShell，运行下面的命令，结果应和 Release 里的 SHA256SUMS.txt 一致。",
        "hashes": "这个版本的 SHA-256：",
        "src_h": "源码和反馈",
        "src": [
            "源码在 GitHub：{repo}，MIT 许可。",
            "使用说明见仓库首页的中文说明（README）。",
            "问题和建议请在 GitHub 上提 Issue；安全问题请按 {security} 私下报告。",
        ],
        "foot1": "© 2026 群星贡献者 · The Qunxing Contributors",
        "foot2": "代码 MIT；数据和文字的许可见各仓库的 LICENSE",
        "privacy": "隐私政策", "privacy_path": "/privacy/", "priv_more": "数据存在哪里、谁会收到、保存多久：见隐私政策。",
    },
    "en": {
        "lang": "en", "path": "/en/download/", "other": "/download/", "other_lang": "zh-CN", "other_label": "中文",
        "title": "Download the Qunxing desktop app · Qunxing",
        "desc": "Download the Qunxing desktop app for Windows: an installer, or a full package that runs without installing. Explore open math problems with the AI subscription you already have; results are checked in Lean.",
        "home": "Home", "lang_nav": "Language", "sp": " ", "bank": "Problems", "bank_path": "/en/problems/", "h1": "Download the Qunxing desktop app",
        "lead": "Explore open math problems on your own computer, with the AI subscription you already have. Results are checked in Lean.",
        "btn_setup": "Download for Windows (installer)", "btn_zip": "Full package (zip, no install)",
        "meta": "Version {v} · {d} · installer {s}", "zip_size": "{s}",
        "mirror": "Slow download? Mirror in mainland China:", "mirror_setup": "installer", "mirror_zip": "full package",
        "notes": "Release notes", "verify_link": "Verify the file", "mac": "Windows only for now; a macOS version is in progress.",
        "soon": "The beta isn’t out yet. Download buttons will appear here when the first version is released.",
        "soon_watch": "To hear about it first: open {repo} on GitHub and choose “Watch → Custom → Releases”.",
        "steps_h": "Get started in three steps",
        "steps": [
            "<b>Install.</b> Run the installer (no administrator rights needed), or unzip the full package anywhere and double-click <code>Qunxing.exe</code>.",
            "<b>First launch.</b> The setup guide helps you pick a work folder, finds the Codex CLI, Claude Code or Gemini CLI already on your computer, and connects one as your console. A subscription or an API key both work.",
            "<b>Draw a problem and run it.</b> Draw an open problem from the bank, check whether it is still open, then let the AI work on it. You can pause, add budget or send a hint at any time. Results that pass both the Lean check and the statement check light a star on the star map.",
        ],
        "req_h": "What you need",
        "req": [
            "Windows 10 or 11, 64-bit.",
            "At least one AI coding tool, signed in: Codex CLI, Claude Code or Gemini CLI.",
            "Lean 4 is optional: you need it only for the Lean check, and the setup guide shows how to install it.",
            "Internet access for drawing problems, bank updates, novelty checks and AI calls. You can also run locally only.",
        ],
        "priv_h": "Privacy",
        "priv": [
            "Nothing is uploaded by default. Run records, proofs and costs stay on your computer.",
            "To submit a result to Qunxing you press “Upload to Qunxing” yourself, in two steps, each with its own consent.",
        ],
        "safe_h": "Safety",
        "smartscreen": "If Windows says “Windows protected your PC”, it is because the app isn’t code-signed yet. Make sure you downloaded it from this page or GitHub, click “More info”, then “Run anyway”.",
        "signed": "The installer and the app are code-signed by the Qunxing project.",
        "verify": "To verify the file, open PowerShell in your download folder and run the command below. The result should match SHA256SUMS.txt in the release.",
        "hashes": "SHA-256 for this version:",
        "src_h": "Source and feedback",
        "src": [
            "Source on GitHub: {repo}, MIT license.",
            "The guide is in the repository’s English README.",
            "Please report problems and ideas as GitHub issues; report security issues privately as described in {security}.",
        ],
        "foot1": "© 2026 The Qunxing Contributors · 群星贡献者",
        "foot2": "Code: MIT; licenses for data and texts are in each repository’s LICENSE",
        "privacy": "Privacy Policy", "privacy_path": "/en/privacy/", "priv_more": "Where data is stored, who receives it and how long it is kept: see the Privacy Policy.",
    },
}

SKY = """  <svg class="field" viewBox="0 0 800 240" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
    <g class="dots">
      <circle class="s t0" cx="612" cy="198" r="1.6"/><circle class="s t1" cx="395" cy="46" r="1.3"/><circle class="s" cx="78" cy="200" r="1.1"/>
      <circle class="s" cx="585" cy="17" r="0.8"/><circle class="s t1" cx="87" cy="150" r="1.6"/><circle class="s t2" cx="377" cy="203" r="1.3"/>
      <circle class="s t0" cx="777" cy="58" r="1.6"/><circle class="s t2" cx="260" cy="100" r="1.3"/><circle class="s" cx="699" cy="118" r="0.8"/>
      <circle class="s" cx="215" cy="70" r="0.8"/><circle class="s t1" cx="267" cy="128" r="1.6"/><circle class="s" cx="507" cy="168" r="0.9"/>
      <circle class="s t2" cx="152" cy="34" r="1.3"/><circle class="s" cx="458" cy="96" r="1.0"/><circle class="s t0" cx="712" cy="214" r="1.3"/>
    </g>
    <g class="figure">
      <polyline class="l" points="560,120 616,98 676,116 712,162 676,200 622,188 560,120"/>
      <circle class="c" cx="560" cy="120" r="2.2"/><circle class="c" cx="616" cy="98" r="2.0"/><circle class="c" cx="676" cy="116" r="2.4"/>
      <circle class="c" cx="676" cy="200" r="2.1"/><circle class="c" cx="622" cy="188" r="1.9"/><circle class="lit" cx="712" cy="162" r="3.2"/>
    </g>
  </svg>"""
MARK = '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M32 6 L37.2 26.8 L58 32 L37.2 37.2 L32 58 L26.8 37.2 L6 32 L26.8 26.8 Z"/></svg>'


def load():
    rel = json.loads(DATA.read_text(encoding="utf-8"))
    if rel.get("schema") != "qunxing.site-release/1":
        raise SystemExit("data/release.json：schema 应为 qunxing.site-release/1")
    if not re.match(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$", rel.get("repo", "")):
        raise SystemExit("data/release.json：repo 格式不对")
    for key in ("setup", "zip"):
        a = rel["assets"][key]
        if not ASSET.match(a.get("name", "")):
            raise SystemExit(f"data/release.json：assets.{key}.name 格式不对")
    if rel.get("available"):
        if not VERSION.match(rel.get("version") or ""):
            raise SystemExit("data/release.json：available 为 true 时，version 要写成 v1.2.3 这样")
        if not DATE.match(rel.get("date") or ""):
            raise SystemExit("data/release.json：date 要写成 2026-12-01 这样")
        for key in ("setup", "zip"):
            a = rel["assets"][key]
            if not isinstance(a.get("size"), int) or a["size"] <= 0 or not HASH.match(a.get("sha256") or ""):
                raise SystemExit(f"data/release.json：assets.{key} 要有正整数 size 和 64 位小写十六进制 sha256")
    return rel


def mb(n):
    return f"{n / 1024 / 1024:.1f} MB"


def link(href, text, cls=None, lang=None):
    attrs = f' class="{cls}"' if cls else ""
    attrs += f' lang="{lang}" hreflang="{lang}"' if lang else ""
    return f'<a{attrs} href="{e(href)}">{text}</a>'


def page(lang, rel):
    t = T[lang]
    repo = rel["repo"]
    repo_url = f"https://github.com/{repo}"
    repo_link = link(repo_url, e(repo))
    security = link(f"{repo_url}/blob/main/SECURITY.md", "SECURITY.md")
    if rel["available"]:
        v, s, z = rel["version"], rel["assets"]["setup"], rel["assets"]["zip"]
        dl = f"{repo_url}/releases/download/{v}/"
        block = [
            f'<p>{link(dl + s["name"], e(t["btn_setup"]), "btn")}</p>',
            f'<p class="meta">{e(t["meta"].format(v=v, d=rel["date"], s=mb(s["size"])))}</p>',
            f'<p>{link(dl + z["name"], e(t["btn_zip"]) + " · " + e(mb(z["size"])), "btn alt")}</p>',
        ]
        if rel.get("mirror"):
            m = f"/download/files/{v}/"
            block.append(f'<p class="meta">{e(t["mirror"])}{t["sp"]}{link(m + s["name"], e(t["mirror_setup"]))} · {link(m + z["name"], e(t["mirror_zip"]))}</p>')
        block.append(f'<p class="meta">{link(f"{repo_url}/releases/tag/{v}", e(t["notes"]))} · {link("#verify", e(t["verify_link"]))} · {e(t["mac"])}</p>')
    else:
        block = [
            f'<p class="status"><span class="dot" aria-hidden="true"></span><span>{e(t["soon"])}</span></p>',
            f'<p class="meta">{e(t["soon_watch"]).format(repo=repo_link)}</p>',
        ]
    safe = [f"<p>{e(t['signed'] if rel.get('signed') else t['smartscreen'])}</p>", f"<p>{e(t['verify'])}</p>",
            f"<pre><code>Get-FileHash .\\{e(rel['assets']['setup']['name'])} -Algorithm SHA256</code></pre>"]
    if rel["available"]:
        rows = "".join(f'<li><code>{e(a["name"])}</code><br><span class="hash">{e(a["sha256"])}</span></li>' for a in (rel["assets"]["setup"], rel["assets"]["zip"]))
        safe.append(f'<p class="muted">{e(t["hashes"])}</p><ul class="hashes">{rows}</ul>')
    items = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    src = [e(x).format(repo=repo_link, security=security) for x in t["src"]]
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>{e(t['title'])}</title>
<meta name="description" content="{e(t['desc'])}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
<link rel="alternate" hreflang="zh-CN" href="/download/">
<link rel="alternate" hreflang="en" href="/en/download/">
</head>
<body>
<header class="sky sky-sm">
{SKY}
  <div class="wrap">
    <div class="top">
      <a class="mark" href="/" aria-label="{e(t['home'])}">{MARK}<span>群星</span><span class="en" lang="en">Qunxing</span></a>
      <nav aria-label="{e(t['lang_nav'])}">{link(t['bank_path'], e(t['bank']))}{link(t['other'], e(t['other_label']), lang=t['other_lang'])}</nav>
    </div>
    <h1>{e(t['h1'])}</h1>
    <p class="lead">{e(t['lead'])}</p>
    <div class="dl">
      {chr(10).join('      ' + b if i else b for i, b in enumerate(block))}
    </div>
  </div>
</header>

<main class="wrap">
  <section>
    <h2>{e(t['steps_h'])}</h2>
    <ol class="steps">{items(t['steps'])}</ol>
  </section>

  <section>
    <h2>{e(t['req_h'])}</h2>
    <ul class="plain">{items(e(x) for x in t['req'])}</ul>
  </section>

  <section>
    <h2>{e(t['priv_h'])}</h2>
    <ul class="plain">{items(e(x) for x in t['priv'])}<li>{link(t['privacy_path'], e(t['priv_more']))}</li></ul>
  </section>

  <section id="verify">
    <h2>{e(t['safe_h'])}</h2>
    {''.join(safe)}
  </section>

  <section>
    <h2>{e(t['src_h'])}</h2>
    <ul class="plain">{items(src)}</ul>
  </section>
</main>

<footer class="wrap">
  <p>{e(t['foot1'])}</p>
  <p>{e(t['foot2'])} · {link(t['privacy_path'], e(t['privacy']))} · <a href="/llms.txt">llms.txt</a></p>
</footer>
</body>
</html>
"""


def main():
    rel = load()
    check = "--check" in sys.argv[1:]
    bad = []
    for lang, path in OUT.items():
        text = page(lang, rel)
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                bad.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if bad:
        print("下载页和 data/release.json 不一致，请运行 python3 tools/build_download.py 后提交：", *bad, sep="\n  ")
        return 1
    print("下载页已检查：与 data/release.json 一致。" if check else "下载页已生成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
