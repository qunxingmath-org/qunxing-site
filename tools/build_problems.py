#!/usr/bin/env python3
"""生成网站的题库：题库首页、按星域的列表、每道题的详情页和 .md，以及 /api/v1 的静态 JSON。

数据来自 qunxing-data 的本地克隆（--data），生成时记下它的提交号（data/bank.json）。
网站的内容安全策略不允许脚本，所以都是生成好的静态文件。

用法：
  python3 tools/build_problems.py --data ../qunxing-data           # 生成
  python3 tools/build_problems.py --data ../qunxing-data --check   # 只检查已提交的文件是否和数据一致（CI 用）
只用标准库。星域、难度档、题型的划分与桌面端相同（协作仓库 contracts/local-api/card_rules.py）。
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
SITE = "https://www.qunxingmath.org"
DATA_REPO = "qunxingmath-org/qunxing-data"
OWNED = ["problems", "en/problems", "p", "api/v1"]   # 本脚本生成并管理的目录（public/ 下），生成前先清空
PER_PAGE = 100
e = html.escape

SECTORS = [  # 键、中文、英文、MSC 主类前两位
    ("combinatorics", "组合", "Combinatorics", "05 06"),
    ("number_theory", "数论", "Number theory", "11"),
    ("algebra", "代数", "Algebra", "08 12 13 14 15 16 17 18 19 20 22"),
    ("analysis", "分析", "Analysis", "26 28 30 31 32 33 34 35 39 40 41 42 43 44 45 46 47 49"),
    ("geometry", "几何", "Geometry", "51 52 53"),
    ("topology", "拓扑", "Topology", "54 55 57 58"),
    ("dynamics", "动力系统", "Dynamical systems", "37"),
    ("probability", "概率统计", "Probability and statistics", "60 62"),
    ("computing", "理论计算机", "Theoretical computer science", "68 94"),
    ("logic", "逻辑", "Logic", "03"),
    ("applied", "交叉与应用", "Applications and interdisciplinary mathematics", "00 01 65 70 74 76 78 80 81 82 83 85 86 90 91 92 93 97"),
    ("unclassified", "未分类", "Unclassified", ""),
]
SECTOR = {k: (zh, en) for k, zh, en, _ in SECTORS}
MSC = {p: k for k, _, _, codes in SECTORS for p in codes.split()}
LEVELS = {"elementary": ("初等", "Entry"), "medium": ("中等", "Intermediate"), "advanced": ("高等", "Advanced"), "legendary": ("传奇", "Legendary"),
          None: ("待补", "Pending")}
KINDS = {"proof": ("证明", "Proof"), "construction": ("构造", "Construction"), "bound": ("求界", "Bound"), "calculation": ("计算", "Calculation"), None: ("待补", "Pending")}
# 文献状态（取自题卡，不是本站的判定）。用词避开"已解决""已验证"。
LIT = {"open": ("开放", "Open"), "partially_solved": ("部分解决", "Partly solved"), "claimed": ("有人声称解决", "Claimed"),
       "solved": ("文献记载已有解答", "Answer reported in the literature"), "disputed": ("有争议", "Disputed"), "unknown": ("不确定", "Unknown")}
NOVELTY = {"not_found_in_scope": ("在所查范围内没找到相同结果", "Nothing identical found in the sources checked"),
           "partial_result": ("找到部分结果", "Partial results found"), "found": ("找到相同结果", "Identical result found"),
           "inconclusive": ("没有定论", "Inconclusive"), "claimed_solution": ("找到有人声称解决的记录", "A claimed solution was found"),
           "known_result": ("找到已知结果", "A known result was found")}
ROLES = {"original": "原始出处", "novelty": "查新依据", "statement": "题面出处", "survey": "综述"}
REFS = {"arxiv": "arXiv", "mo": "MathOverflow", "mse": "Math StackExchange", "erdos": "Erdős Problems", "opg": "Open Problem Garden", "oeis": "OEIS"}
FORMAL = {"none": ("没有", "None"), "statement": ("有形式化陈述", "Formal statement"), "proof": ("有形式化证明", "Formal proof")}
FLAGS = {"draft": ("草稿", "Draft"), "weak_evidence": ("开放状态证据较弱", "Weak open-status evidence"),
         "statement_disputed": ("题面有异议", "Disputed statement"), "verification_track": ("验证轨道", "Verification track")}


# ---------- 题卡 ----------
def sector_of(meta):
    return MSC.get(str((meta.get("msc2020") or {}).get("primary") or "")[:2], "unclassified")


def band_of(meta):
    lv = (meta.get("difficulty") or {}).get("level")
    # 难度 5 只给"传奇"：提出 30 年以上、领域外也有名、公认极难（题卡格式 3.10）
    return None if lv is None else "elementary" if lv <= 2 else "medium" if lv == 3 else "advanced" if lv == 4 else "legendary"


def kind_of(meta):
    a = meta.get("answer_type")
    if a in {"proof", "yes_no", "classification", "formal_artifact"}:
        return "proof"
    if a == "object":
        return "construction"
    if a == "bound":
        return "bound"
    if a == "value" and meta.get("checkability") == "decidable":
        return "calculation"
    return None


def flags_of(meta):
    out = []
    if meta.get("card_status") == "draft":
        out.append("draft")
    if (meta.get("informal_status") or {}).get("strength") == "weak":
        out.append("weak_evidence")
    if meta.get("statement_disputed") is True or (meta.get("statement_audit") or {}).get("verdict") == "fail":
        out.append("statement_disputed")
    if meta.get("track") == "verify":
        out.append("verification_track")
    return out


def load(data):
    cards = []
    for mp in sorted((data / "problems").glob("*/QX-P-*.meta.json")):
        meta = json.loads(mp.read_text(encoding="utf-8"))
        if meta.get("visibility") != "public":
            continue
        tp = mp.with_name(mp.name.replace(".meta.json", ".text.md"))
        text = tp.read_text(encoding="utf-8") if tp.exists() else ""
        cards.append({"meta": meta, "meta_raw": mp.read_bytes(), "text": text, "sector": sector_of(meta), "band": band_of(meta), "kind": kind_of(meta)})
    cards.sort(key=lambda c: c["meta"]["id"])
    return cards


# ---------- 极简 Markdown（题卡正文用到的：标题、段落、列表、引用、表格、粗体、代码、网址） ----------
URL = re.compile(r"https?://[^\s<>\"'）)，。；、]+")


def inline(s):
    s = e(s, quote=True)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return URL.sub(lambda m: f'<a href="{m.group(0)}" rel="nofollow noopener">{m.group(0)}</a>', s)


def md(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.split("\n")
    out, i, skipped_h1 = [], 0, False
    para = []

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(x.strip()) for x in para) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            flush(); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            flush()
            level = len(m.group(1))
            if level == 1 and not skipped_h1:
                skipped_h1 = True; i += 1; continue   # 题目标题已经在页面顶部
            tag = "h" + str(min(6, max(2, level)))
            out.append(f"<{tag}>{inline(m.group(2))}</{tag}>"); i += 1; continue
        if st.startswith(">"):
            flush()
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + md_inner(block) + "</blockquote>"); continue
        if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            flush()
            head = [c.strip() for c in st.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'); continue
        if re.match(r"^\s*[-*]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
            flush()
            ordered = bool(re.match(r"^\s*\d+\.\s+", ln))
            items = []
            while i < len(lines) and lines[i].strip():
                cur = lines[i]
                mm = re.match(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)$", cur)
                if mm:
                    items.append([len(mm.group(1)), mm.group(2)])
                elif items:
                    items[-1][1] += " " + cur.strip()
                else:
                    break
                i += 1
            out.append(render_list(items, ordered)); continue
        para.append(ln); i += 1
    flush()
    return "\n".join(out)


def md_inner(lines):
    return md("\n".join(["# _"] + lines)) if lines else ""


def render_list(items, ordered):
    tag = "ol" if ordered else "ul"
    base = min(x[0] for x in items)
    html_out, stack = [f"<{tag}>"], [base]
    for indent, txt in items:
        if indent > stack[-1]:
            html_out.append("<ul>"); stack.append(indent)
        while indent < stack[-1] and len(stack) > 1:
            html_out.append("</ul>"); stack.pop()
        html_out.append(f"<li>{inline(txt)}</li>")
    while len(stack) > 1:
        html_out.append("</ul>"); stack.pop()
    html_out.append(f"</{tag}>")
    return "".join(html_out)


# ---------- 页面 ----------
MARK = '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M32 6 L37.2 26.8 L58 32 L37.2 37.2 L32 58 L26.8 37.2 L6 32 L26.8 26.8 Z"/></svg>'
UI = {
    "zh": {"lang": "zh-CN", "bank": "题库", "download": "下载", "other": "English", "other_lang": "en", "home": "首页",
           "foot1": "© 2026 群星贡献者 · The Qunxing Contributors",
           "foot2": "题卡文字 CC BY-SA 4.0；结构化字段 CC0 1.0；引用的原文片段保持原许可。本站不验证题目状态和任何提交。"},
    "en": {"lang": "en", "bank": "Problems", "download": "Download", "other": "中文", "other_lang": "zh-CN", "home": "Home",
           "foot1": "© 2026 The Qunxing Contributors · 群星贡献者",
           "foot2": "Card texts CC BY-SA 4.0; structured fields CC0 1.0; quoted source passages keep their original licenses. This site does not verify problem status or any submission."},
}


def lab(pair, lang):
    return pair[0] if lang == "zh" else pair[1]


def page(lang, title, desc, body, path, other_path=None, alternates=""):
    u = UI[lang]
    bank = "/problems/" if lang == "zh" else "/en/problems/"
    dl = "/download/" if lang == "zh" else "/en/download/"
    nav = f'<a href="{bank}">{e(u["bank"])}</a><a class="hl" href="{dl}">{e(u["download"])}</a>'
    if other_path:
        nav += f'<a href="{other_path}" lang="{u["other_lang"]}" hreflang="{u["other_lang"]}">{e(u["other"])}</a>'
    return f"""<!doctype html>
<html lang="{u['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
<link rel="canonical" href="{SITE}{path}">
{alternates}</head>
<body>
<header class="sky sky-xs">
  <div class="wrap wide">
    <div class="top">
      <a class="mark" href="/" aria-label="{e(u['home'])}">{MARK}<span>群星</span><span class="en" lang="en">Qunxing</span></a>
      <nav aria-label="{e(u['bank'])}">{nav}</nav>
    </div>
  </div>
</header>
<main class="wrap wide bank">
{body}
</main>
<footer class="wrap wide">
  <p>{e(u['foot1'])}</p>
  <p>{e(u['foot2'])} · <a href="/llms.txt">llms.txt</a></p>
</footer>
</body>
</html>
"""


def disclaimer(lang):
    return ('<p class="disclaimer"><b>本站不验证。</b>题目状态来自文献和题卡整理者的记录，没有经过本站核验；任何提交在本站都不算"已验证"。</p>' if lang == "zh" else
            '<p class="disclaimer"><b>This site does not verify.</b> Problem status comes from the literature and the card maintainers’ records; it has not been checked by this site, and no submission counts as verified here.</p>')


def overview(lang, cards, commit):
    zh = lang == "zh"
    root = "/problems/" if zh else "/en/problems/"
    by = {}
    for c in cards:
        by.setdefault(c["sector"], []).append(c)
    lit = {}
    for c in cards:
        v = (c["meta"].get("informal_status") or {}).get("value") or "unknown"
        lit[v] = lit.get(v, 0) + 1
    tiles = "".join(f'<li><a href="{root}{k}/"><b>{e(lab(SECTOR[k], lang))}</b><span class="n">{len(by[k])}</span></a></li>'
                    for k, *_ in SECTORS if k in by)
    lits = " · ".join(f"{e(lab(LIT.get(k, (k, k)), lang))} {n}" for k, n in sorted(lit.items(), key=lambda x: -x[1]))
    src = f'<a href="https://github.com/{DATA_REPO}/tree/{commit}">{DATA_REPO}@{commit[:7]}</a>'
    nleg = sum(1 for c in cards if c["band"] == "legendary")
    legend_link = "" if not nleg else (
        f'<p class="legend-link"><a href="{root}legendary/"><b>传奇</b> · {nleg} 道久未解决的著名猜想</a></p>' if zh else
        f'<p class="legend-link"><a href="{root}legendary/"><b>Legendary</b> · {nleg} famous long-standing conjectures</a></p>')
    if zh:
        body = f"""<h1>群星题库</h1>
<p class="lead2">{len(cards)} 道开放数学问题，来自期刊、问题集和问答站。每道题有题面、人话版、原文摘录、来源和查新记录。</p>
{disclaimer(lang)}
{legend_link}
<h2>按星域浏览</h2>
<ul class="tiles">{tiles}</ul>
<p class="muted small">文献状态：{lits}。所有题目目前都暂无提交（<code>no_submission</code>）。</p>
<h2>想动手试试</h2>
<p>在群星桌面端里抽一道题，让你自己的 AI 去探索，结果用 Lean 检查。</p>
<p class="cta-en"><a class="btn" href="/download/">下载桌面端 · Windows</a></p>
<h2>给 Agent 和程序</h2>
<ul class="plain">
<li>题目列表：<a href="/api/v1/problems.json">/api/v1/problems.json</a>；每道题的完整题卡：<code>/api/v1/problems/&lt;编号&gt;.json</code></li>
<li>每个题目页都有 Markdown 版：在网址后加 <code>.md</code>，例如 <a href="/p/QX-P-000001.md">/p/QX-P-000001.md</a></li>
<li>网站说明：<a href="/llms.txt">/llms.txt</a></li>
</ul>
<p class="muted small">数据来源：{src}。题卡文字 CC BY-SA 4.0，结构化字段 CC0 1.0。</p>"""
        return page(lang, "群星题库 · 群星 Qunxing", f"群星题库：{len(cards)} 道开放数学问题，按星域浏览，每道题有题面、人话版、来源和查新记录。", body, root, "/en/problems/")
    body = f"""<h1>The Qunxing problem bank</h1>
<p class="lead2">{len(cards)} open math problems from journals, problem collections and Q&amp;A sites. Each has a statement, a plain-language summary (in Chinese), source quotes, references and a novelty-check record.</p>
{disclaimer(lang)}
{legend_link}
<h2>Browse by sector</h2>
<ul class="tiles">{tiles}</ul>
<p class="muted small">Literature status: {lits}. No problem has submissions yet (<code>no_submission</code>).</p>
<h2>Try one yourself</h2>
<p>Draw a problem in the Qunxing desktop app, let your own AI explore it, and check the result in Lean.</p>
<p class="cta-en"><a class="btn" href="/en/download/">Download for Windows</a></p>
<h2>For agents and programs</h2>
<ul class="plain">
<li>Problem list: <a href="/api/v1/problems.json">/api/v1/problems.json</a>; full card for each problem: <code>/api/v1/problems/&lt;id&gt;.json</code></li>
<li>Every problem page has a Markdown version: add <code>.md</code> to the URL, e.g. <a href="/p/QX-P-000001.md">/p/QX-P-000001.md</a></li>
<li>Site guide: <a href="/llms.txt">/llms.txt</a></li>
</ul>
<p class="muted small">Data source: {src}. Card texts CC BY-SA 4.0; structured fields CC0 1.0.</p>"""
    return page(lang, "The Qunxing problem bank · Qunxing", f"The Qunxing problem bank: {len(cards)} open math problems by sector, each with a statement, sources and a novelty-check record.", body, root, "/problems/")


def lit_text(meta, lang, date=True):
    s = meta.get("informal_status") or {}
    parts = [lab(LIT.get(s.get("value") or "unknown", (s.get("value"), s.get("value"))), lang)]
    if s.get("strength") == "weak":
        parts.append("证据较弱" if lang == "zh" else "weak evidence")
    if date and s.get("as_of"):
        parts.append(("截至 " if lang == "zh" else "as of ") + s["as_of"])
    return " · ".join(parts)


def sector_pages(lang, key, items):
    zh = lang == "zh"
    root = ("/problems/" if zh else "/en/problems/") + key + "/"
    other = ("/en/problems/" if zh else "/problems/") + key + "/"
    pages = [items[i:i + PER_PAGE] for i in range(0, len(items), PER_PAGE)] or [[]]
    name = lab(SECTOR[key], lang)
    out = {}
    for n, chunk in enumerate(pages, 1):
        path = root if n == 1 else f"{root}{n}/"
        opath = other if n == 1 else f"{other}{n}/"
        rows = []
        for c in chunk:
            m = c["meta"]
            title = m.get("title") if zh else (m.get("title_en") or m.get("title"))
            nv = (m.get("novelty") or {}).get("last_checked_at") or "—"
            rows.append(f'<tr><td class="mono"><a href="/p/{e(m["id"])}/">{e(m["id"])}</a></td><td>{e(title or "")}</td>'
                        f'<td>{e(lab(LEVELS[c["band"]], lang))}</td><td>{e(lit_text(m, lang, date=False))}</td><td class="mono">{e(nv)}</td></tr>')
        head = ("<th>编号</th><th>题目</th><th>难度</th><th>文献状态</th><th>最近查新</th>" if zh else
                "<th>ID</th><th>Problem</th><th>Difficulty</th><th>Literature status</th><th>Last novelty check</th>")
        pager = ""
        if len(pages) > 1:
            prev = f'<a href="{root if n == 2 else f"{root}{n - 1}/"}">{"上一页" if zh else "Previous"}</a>' if n > 1 else ""
            nxt = f'<a href="{root}{n + 1}/">{"下一页" if zh else "Next"}</a>' if n < len(pages) else ""
            cur = ' aria-current="page"'
            nums = " ".join(f'<a href="{root if k == 1 else f"{root}{k}/"}"{cur if k == n else ""}>{k}</a>' for k in range(1, len(pages) + 1))
            pager = f'<nav class="pager" aria-label="{"分页" if zh else "Pages"}">{prev} {nums} {nxt}</nav>'
        crumbs = f'<nav class="crumbs" aria-label="{"位置" if zh else "Breadcrumb"}"><a href="{"/problems/" if zh else "/en/problems/"}">{"题库" if zh else "Problems"}</a> › {e(name)}</nav>'
        count = f"{len(items)} 道" if zh else f"{len(items)} problems"
        body = f"""{crumbs}
<h1>{e(name)} <span class="count">{e(count)}</span></h1>
{disclaimer(lang)}
<div class="tbl"><table class="plist"><thead><tr>{head}</tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table></div>
{pager}"""
        title = (f"{name} · 群星题库" if zh else f"{name} · Qunxing problem bank") + (f"（第 {n} 页）" if zh and n > 1 else f" (page {n})" if n > 1 else "")
        desc = f"群星题库里{name}方向的 {len(items)} 道开放问题。" if zh else f"{len(items)} open problems in {name} in the Qunxing problem bank."
        out[path] = page(lang, title, desc, body, path, opath)
    return out


def legend_reason(meta):
    """difficulty.note 开头"传奇：……"的那一句；没有就返回空串"""
    note = str((meta.get("difficulty") or {}).get("note") or "")
    if not note.startswith("传奇："):
        return ""
    return note[3:].split(" 原作者的说明：")[0].strip()


def legend_page(lang, cards):
    zh = lang == "zh"
    root = "/problems/legendary/" if zh else "/en/problems/legendary/"
    other = "/en/problems/legendary/" if zh else "/problems/legendary/"
    items = sorted((c for c in cards if c["band"] == "legendary"), key=lambda c: (c["meta"].get("track") != "open", c["meta"]["id"]))
    rows = []
    for c in items:
        m = c["meta"]
        title = m.get("title") if zh else (m.get("title_en") or m.get("title"))
        track = ("开放问题" if zh else "Open problem") if m.get("track") == "open" else ("核对证明声明" if zh else "Check a claimed proof")
        why = legend_reason(m) if zh else ""
        rows.append(f'<tr><td class="mono"><a href="/p/{e(m["id"])}/">{e(m["id"])}</a></td><td>{e(title or "")}'
                    + (f'<div class="muted small">{e(why)}</div>' if why else "")
                    + f'</td><td>{e(lab(SECTOR[c["sector"]], lang))}</td><td>{e(track)}</td><td>{e(lit_text(m, lang, date=False))}</td></tr>')
    head = ("<th>编号</th><th>题目</th><th>星域</th><th>轨道</th><th>文献状态</th>" if zh else
            "<th>ID</th><th>Problem</th><th>Sector</th><th>Track</th><th>Literature status</th>")
    crumbs = f'<nav class="crumbs" aria-label="{"位置" if zh else "Breadcrumb"}"><a href="{"/problems/" if zh else "/en/problems/"}">{"题库" if zh else "Problems"}</a> › {"传奇" if zh else "Legendary"}</nav>'
    if zh:
        intro = ("<p>难度分四档：初等、中等、高等、传奇。<b>传奇</b>只给三条都满足的题：提出 30 年以上仍未解决；在本领域之外也有名"
                 "（有自己的百科词条、收进著名问题清单，或者有悬赏）；公认极难。</p>"
                 "<p>\"核对证明声明\"的题，是有人声称证明了这个猜想，等待核对。</p>")
        body = f"{crumbs}\n<h1>传奇 <span class=\"count\">{len(items)} 道</span></h1>\n{intro}\n{disclaimer(lang)}\n"
        title, desc = "传奇 · 群星题库", f"群星题库里的 {len(items)} 道传奇题：提出 30 年以上仍未解决、在本领域之外也有名的猜想。"
    else:
        intro = ("<p>Difficulty has four tiers: Entry, Intermediate, Advanced and Legendary. A problem is <b>Legendary</b> only if all three hold: "
                 "it has been open for 30+ years; it is famous beyond its field (its own encyclopedia entry, a famous problem list, or a prize); "
                 "and it is widely considered extremely hard. The one-line reasons are on the Chinese page.</p>"
                 "<p>“Check a claimed proof” means someone has claimed a proof of the conjecture and it is waiting to be checked.</p>")
        body = f"{crumbs}\n<h1>Legendary <span class=\"count\">{len(items)} problems</span></h1>\n{intro}\n{disclaimer(lang)}\n"
        title, desc = "Legendary · Qunxing problem bank", f"{len(items)} legendary problems in the Qunxing problem bank: famous conjectures open for 30+ years."
    body += f"""<div class="tbl"><table class="plist"><thead><tr>{head}</tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table></div>"""
    return root, page(lang, title, desc, body, root, other)


def detail(c, commit):
    m, key = c["meta"], c["sector"]
    pid = m["id"]
    chips = [lab(SECTOR[key], "zh"), lab(KINDS[c["kind"]], "zh"), lab(LEVELS[c["band"]], "zh"), "开放问题" if m.get("track") == "open" else "验证"]
    chips = "".join(f'<span class="chip{" legend" if x == LEVELS["legendary"][0] else ""}">{e(x)}</span>' for x in chips) + "".join(f'<span class="chip warn">{e(lab(FLAGS[f], "zh"))}</span>' for f in flags_of(m))
    nv = m.get("novelty") or {}
    scope = (nv.get("scope") or {}).get("sources") or []
    nv_txt = " · ".join(x for x in [nv.get("last_checked_at"), lab(NOVELTY.get(nv.get("result"), (nv.get("result") or "", "")), "zh") if nv.get("result") else None,
                                     f"查了 {len(scope)} 个来源" if scope else None] if x) or "还没有查新记录"
    fs = m.get("formal_status") or {}
    msc = m.get("msc2020") or {}
    msc_txt = " · ".join(x for x in [msc.get("primary"), " ".join(msc.get("secondary") or [])] if x) or "—"
    kv = [("文献状态", e(lit_text(m, "zh"))), ("形式化", e(lab(FORMAL.get(fs.get("value"), (fs.get("value") or "—", "")), "zh"))),
          ("最近查新", e(nv_txt)), ("MSC", f'<span class="mono">{e(msc_txt)}</span>')]
    if m.get("proposer"):
        kv.append(("提出者", e(m["proposer"])))
    if m.get("first_published"):
        kv.append(("首次发表", e(m["first_published"])))
    kv_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in kv)
    srcs = []
    for s in m.get("sources") or []:
        label = e(s.get("cite") or s.get("url") or "")
        link = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else None)
        role = ROLES.get(s.get("role"), s.get("role") or "")
        anchor = f'<a href="{e(link)}" rel="nofollow noopener">{label}</a>' if link and re.match(r"^https?://", link) else label
        note = f' <span class="muted">（{e(role)}）</span>' if role else ""
        srcs.append(f"<li>{anchor}{note}</li>")
    for r in m.get("external_refs") or []:
        if r.get("url") and re.match(r"^https?://", r["url"]):
            name = REFS.get(r.get("source"), (r.get("source") or "").upper())
            srcs.append(f'<li><a href="{e(r["url"])}" rel="nofollow noopener">{e(name)} {e(str(r.get("id") or ""))}</a></li>')
    src_html = ('<ul class="plain">' + "".join(srcs) + "</ul>") if srcs else '<p class="muted">题卡里没有列出来源。</p>'
    cite = f"群星题库 {pid}（card_rev {m.get('card_rev', '')}），{SITE}/p/{pid}/"
    body = f"""<nav class="crumbs" aria-label="位置"><a href="/problems/">题库</a> › <a href="/problems/{key}/">{e(lab(SECTOR[key], "zh"))}</a> › <span class="mono">{e(pid)}</span></nav>
<h1 class="ptitle">{e(m.get("title") or pid)}</h1>
{f'<p class="ptitle-en" lang="en">{e(m["title_en"])}</p>' if m.get("title_en") else ""}
<p class="chips">{chips}</p>
{disclaimer("zh")}
<section class="summary" aria-label="聚合摘要">
  <p><span class="badge">暂无提交 <code>no_submission</code></span></p>
  <p class="verify">本站是否验证：否（site_verified: false）</p>
  <dl class="kv">{kv_html}</dl>
</section>
<article class="md">
{md(c["text"])}
</article>
<section class="sec">
  <h2>来源</h2>
  {src_html}
</section>
<section class="sec">
  <h2>失败路径</h2>
  <p>尚未记录失败路径。用群星桌面端探索这道题，结束时可以自己决定是否匿名提交失败路径。</p>
</section>
<section class="sec">
  <h2>引用与导出</h2>
  <p>引用：{e(cite)}</p>
  <p><a href="/p/{e(pid)}.md">Markdown 版</a> · <a href="/api/v1/problems/{e(pid)}.json">JSON（完整题卡）</a> · <a href="https://github.com/{DATA_REPO}/blob/{commit}/problems/{e(pid[5:8])}/{e(pid)}.text.md">在 GitHub 上看题卡</a>（题面有问题？在 qunxing-data 开 Issue，选"题面异议"）</p>
</section>
<p class="cta-en"><a class="btn" href="/download/">在群星桌面端里探索这道题</a></p>"""
    one = re.search(r"\*\*一句话\*\*[：:]\s*(.+)", c["text"])
    desc = (one.group(1).replace("**", "").strip() if one else (m.get("title_en") or m.get("title") or pid))[:150]
    alt = f'<link rel="alternate" type="text/markdown" href="/p/{e(pid)}.md">\n<link rel="alternate" type="application/json" href="/api/v1/problems/{e(pid)}.json">\n'
    return page("zh", f"{pid} {m.get('title') or ''} · 群星题库"[:120], desc, body, f"/p/{pid}/", None, alt)


def evidence_api(cards, data, commit):
    if data is None or not (data / "evidence").is_dir():
        return {}
    files = {"api/v1/vocab.json": (data / "schema/qunxing.vocab-1.json").read_bytes()}
    items = []
    for card in cards:
        pid = card["meta"]["id"]
        raw = (data / "evidence" / pid[5:8] / f"{pid}.json").read_bytes()
        evidence = json.loads(raw)
        files[f"api/v1/evidence/{pid}.json"] = raw
        summary = evidence["summary"]
        states = {dimension: summary[dimension]["value"] for dimension in
                  ("math_status", "formal_evidence", "search_coverage", "math_status_proposed") if dimension in summary}
        if "claim" in summary:
            states["claim"] = {key: value for key, value in summary["claim"].items() if key in ("state", "review")}
        items.append({"id": pid, "card_rev": evidence["card_rev"], "summary": states,
                      "url": f"{SITE}/api/v1/evidence/{pid}.json"})
    index = {"schema": "qunxing.site-evidence/1", "source": {"repo": DATA_REPO, "commit": commit},
             "vocabulary": f"{SITE}/api/v1/vocab.json", "count": len(items), "items": items}
    files["api/v1/evidence.json"] = (json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return files


def api(cards, commit, data=None):
    src = {"repo": DATA_REPO, "commit": commit}
    lic = {"metadata": "CC0-1.0", "text": "CC-BY-SA-4.0", "note": "Quoted source passages keep their original licenses."}
    def item(c):
        m = c["meta"]
        return {"id": m["id"], "title": m.get("title"), "title_en": m.get("title_en"), "sector": c["sector"], "msc": (m.get("msc2020") or {}).get("primary"),
                "difficulty_band": c["band"], "question_kind": c["kind"], "track": m.get("track"), "status": (m.get("informal_status") or {}).get("value"),
                "card_rev": m.get("card_rev"), "updated": (m.get("novelty") or {}).get("last_checked_at") or (m.get("informal_status") or {}).get("as_of"),
                "url": f"{SITE}/p/{m['id']}/", "md": f"{SITE}/p/{m['id']}.md", "json": f"{SITE}/api/v1/problems/{m['id']}.json"}
    dump = lambda o: (json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    files = {"api/v1/problems.json": dump({"schema": "qunxing.site-problems/1", "source": src, "license": lic, "count": len(cards), "items": [item(c) for c in cards]})}
    sectors = {}
    for c in cards:
        sectors.setdefault(c["sector"], []).append(item(c))
        files[f"api/v1/problems/{c['meta']['id']}.json"] = c["meta_raw"]
    for k, items in sectors.items():
        files[f"api/v1/problems/by-sector/{k}.json"] = dump({"schema": "qunxing.site-problems/1", "source": src, "license": lic, "sector": k, "count": len(items), "items": items})
    links = {"problems": f"{SITE}/api/v1/problems.json", "problem": f"{SITE}/api/v1/problems/{{id}}.json", "by_sector": f"{SITE}/api/v1/problems/by-sector/{{sector}}.json"}
    evidence = evidence_api(cards, data, commit)
    if evidence:
        files.update(evidence)
        links.update(evidence=f"{SITE}/api/v1/evidence.json", problem_evidence=f"{SITE}/api/v1/evidence/{{id}}.json",
                     vocabulary=f"{SITE}/api/v1/vocab.json")
    files["api/v1/index.json"] = (json.dumps({"schema": "qunxing.site-api/1", "version": "v1", "source": src, "license": lic,
        "files": links,
        "sectors": sorted(sectors)}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files


def data_commit(data):
    commit = subprocess.run(["git", "-C", str(data), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if not re.match(r"^[0-9a-f]{40}$", commit):
        raise SystemExit("取不到 qunxing-data 的提交号")
    return commit


def build(data, api_data=None):
    commit = data_commit(data)
    cards = load(data)
    if not cards:
        raise SystemExit("没有读到题卡：--data 应指向 qunxing-data 的克隆")
    files = {}
    for lang, base in (("zh", "problems/"), ("en", "en/problems/")):
        files[base + "index.html"] = overview(lang, cards, commit).encode("utf-8")
        by = {}
        for c in cards:
            by.setdefault(c["sector"], []).append(c)
        for k, items in by.items():
            for path, text in sector_pages(lang, k, items).items():
                files[path.lstrip("/") + "index.html"] = text.encode("utf-8")
        if any(c["band"] == "legendary" for c in cards):
            path, text = legend_page(lang, cards)
            files[path.lstrip("/") + "index.html"] = text.encode("utf-8")
    for c in cards:
        pid = c["meta"]["id"]
        files[f"p/{pid}/index.html"] = detail(c, commit).encode("utf-8")
        files[f"p/{pid}.md"] = c["text"].encode("utf-8")
    if api_data is not None and api_data != data:
        files.update(api(load(api_data), data_commit(api_data), api_data))
    else:
        files.update(api(cards, commit, data))
    bank = (json.dumps({"schema": "qunxing.site-bank/1", "source": {"repo": DATA_REPO, "commit": commit}, "count": len(cards)}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files, bank


def existing():
    out = {}
    for d in OWNED:
        base = PUBLIC / d
        if base.exists():
            for f in base.rglob("*"):
                if f.is_file():
                    out[str(f.relative_to(PUBLIC)).replace("\\", "/")] = f.read_bytes()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True, help="qunxing-data 的本地克隆")
    ap.add_argument("--api-data", type=Path, help="Separate frozen data checkout for static JSON only")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files, bank = build(a.data.resolve(), a.api_data.resolve() if a.api_data else None)
    api_bank = None
    if a.api_data:
        index = json.loads(files["api/v1/problems.json"])
        api_bank = (json.dumps({"schema": "qunxing.site-bank/1", "source": index["source"],
                               "count": index["count"]}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if a.check:
        have = existing()
        bad = sorted(set(files) ^ set(have)) + sorted(k for k in files if k in have and have[k] != files[k])
        bank_path = ROOT / "data" / "bank.json"
        if not bank_path.exists() or bank_path.read_bytes() != bank:
            bad.append("data/bank.json")
        if api_bank is not None:
            api_bank_path = ROOT / "data/api-bank.json"
            if not api_bank_path.exists() or api_bank_path.read_bytes() != api_bank:
                bad.append("data/api-bank.json")
        if bad:
            print(f"题库页面和数据不一致（{len(bad)} 个文件），请运行 python3 tools/build_problems.py --data <qunxing-data> 后提交。前几个：", *bad[:10], sep="\n  ")
            return 1
        print(f"题库已检查：{len(files)} 个文件与 data/bank.json 记录的数据一致。")
        return 0
    for d in OWNED:
        target = PUBLIC / d
        if target.exists():
            shutil.rmtree(target)
    for rel, data in files.items():
        p = PUBLIC / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "bank.json").write_bytes(bank)
    if api_bank is not None:
        (ROOT / "data/api-bank.json").write_bytes(api_bank)
    print(f"题库已生成：{len(files)} 个文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
