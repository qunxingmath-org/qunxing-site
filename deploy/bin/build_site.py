#!/usr/bin/env python3
"""Build a static site artifact without modifying the checked-out sources."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote
from xml.etree import ElementTree as xml

from release_assets import latest, mirror_present

ROOT = Path(__file__).resolve().parents[2]
HOST = "https://www.qunxingmath.org"
SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"


def run_builder(stage, script, *args):
    subprocess.run([sys.executable, str(stage/"tools"/script), *map(str, args)], cwd=stage, check=True)


def sitemap(public):
    xml.register_namespace("", SITEMAP)
    result = xml.Element(f"{{{SITEMAP}}}urlset")
    for page in sorted(public.rglob("index.html")):
        folder = page.parent.relative_to(public)
        path = "/" if folder == Path(".") else "/" + quote(folder.as_posix()) + "/"
        element = xml.SubElement(result, f"{{{SITEMAP}}}url")
        xml.SubElement(element, f"{{{SITEMAP}}}loc").text = HOST + path
    xml.ElementTree(result).write(public/"sitemap.xml", encoding="utf-8", xml_declaration=True)


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.inside = True

    def handle_endtag(self, tag):
        if tag == "main":
            self.inside = False

    def handle_data(self, text):
        if self.inside and text.strip():
            self.blocks.append(text.strip())


def full_text(public):
    source = (public/"llms.txt").read_text(encoding="utf-8")
    paths = dict.fromkeys(re.findall(r"\]\(https://www\.qunxingmath\.org(/[^)\s]*)\)", source))
    copies = [source.rstrip()]
    for path in paths:
        if not path.endswith("/"):
            continue
        file = public/path.strip("/")/"index.html"
        parser = MainText()
        parser.feed(file.read_text(encoding="utf-8"))
        if parser.blocks:
            copies.extend((f"\n## {HOST}{path}", "\n".join(parser.blocks)))
    (public/"llms-full.txt").write_text("\n\n".join(copies) + "\n", encoding="utf-8")


def build(data, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qx-site-build-", dir=output.parent) as staging:
        stage = Path(staging)
        for name in ("tools", "public", "data"):
            shutil.copytree(ROOT/name, stage/name)
        run_builder(stage, "build_problems.py", "--data", data)
        release = latest()
        release_file = stage/"data/release.json"
        if release is None:
            existing = json.loads(release_file.read_text(encoding="utf-8"))
            if existing["available"]:
                raise ValueError("A published desktop release is missing from GitHub")
        else:
            release["mirror"] = mirror_present(release)
            release_file.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
        run_builder(stage, "build_download.py")
        public = stage/"public"
        sitemap(public)
        full_text(public)
        (public/"data").mkdir(exist_ok=True)
        shutil.copy2(release_file, public/"data/release.json")
        public.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.data.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
