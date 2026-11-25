"""Read the public desktop Release and publish a verified local mirror directory."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = "qunxingmath-org/qunxing-app"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSETS = {"setup": "Qunxing-Setup.exe", "zip": "Qunxing-Windows-x64.zip"}
SUMS = "SHA256SUMS.txt"
VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.]+)?")
DIGEST = re.compile(r"[0-9a-fA-F]{64}")


def fetch(url, timeout=30):
    return urlopen(Request(url, headers={"User-Agent": "Qunxing-site-build"}), timeout=timeout)


def asset_url(version, name):
    return f"https://github.com/{REPO}/releases/download/{version}/{name}"


def read_sums(text):
    files = {}
    for row in text.splitlines():
        if not row.strip():
            continue
        checksum, name = row.split(maxsplit=1)
        name = name.lstrip("*")
        if not DIGEST.fullmatch(checksum) or name in files:
            raise ValueError("Invalid SHA256SUMS.txt")
        files[name] = checksum.lower()
    return files


def latest():
    try:
        with fetch(API) as response:
            release = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            error.close()
            return None
        raise
    version = release["tag_name"]
    if not VERSION.fullmatch(version) or release["draft"] or release["prerelease"]:
        raise ValueError("The latest desktop release is not a published stable version")
    metadata = {asset["name"]: asset for asset in release["assets"]}
    with fetch(asset_url(version, SUMS)) as response:
        sums = read_sums(response.read(65537).decode("utf-8-sig"))
    assets = {}
    for role, name in ASSETS.items():
        asset = metadata[name]
        checksum = sums[name]
        digest = asset.get("digest")
        if asset["size"] <= 0 or digest and digest != f"sha256:{checksum}":
            raise ValueError(f"Release asset metadata does not match SHA256SUMS.txt: {name}")
        assets[role] = {"name": name, "size": asset["size"], "sha256": checksum}
    return {"schema": "qunxing.site-release/1", "repo": REPO, "available": True,
            "version": version, "date": datetime.fromisoformat(release["published_at"]).date().isoformat(),
            "signed": False, "mirror": False, "assets": assets}


def sums_text(release):
    return "".join(f'{asset["sha256"]}  {asset["name"]}\n' for asset in release["assets"].values())


def mirror_present(release):
    host = "https://www.qunxingmath.org"
    url = f'{host}/download/files/{release["version"]}/{SUMS}'
    try:
        with fetch(url) as response:
            observed = read_sums(response.read(65537).decode("utf-8-sig"))
    except HTTPError as error:
        if error.code == 404:
            error.close()
            return False
        raise
    return observed == {a["name"]: a["sha256"] for a in release["assets"].values()}


def verify_file(path, metadata):
    with path.open("rb") as file:
        found = sha256()
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            found.update(chunk)
    if path.stat().st_size != metadata["size"] or found.hexdigest() != metadata["sha256"]:
        raise ValueError(f"Release SHA-256 or size mismatch: {path.name}")


def sync_mirror(release, output):
    version = release["version"]
    output.mkdir(parents=True, exist_ok=True)
    target = output / version
    if target.is_dir():
        for asset in release["assets"].values():
            verify_file(target / asset["name"], asset)
        if (target / SUMS).read_text(encoding="ascii") != sums_text(release):
            raise ValueError(f"Published mirror checksum file does not match: {version}")
        return target
    with tempfile.TemporaryDirectory(prefix=".incoming-", dir=output.parent) as temporary:
        incoming = Path(temporary) / version
        incoming.mkdir()
        for asset in release["assets"].values():
            path = incoming / asset["name"]
            with fetch(asset_url(version, asset["name"]), timeout=90) as response, path.open("xb") as file:
                checksum, size = sha256(), 0
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > asset["size"]:
                        raise ValueError(f"Release asset exceeded declared size: {path.name}")
                    checksum.update(chunk)
                    file.write(chunk)
                if size != asset["size"] or checksum.hexdigest() != asset["sha256"]:
                    raise ValueError(f"Release SHA-256 or size mismatch: {path.name}")
        (incoming / SUMS).write_text(sums_text(release), encoding="ascii", newline="\n")
        incoming.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    release = latest()
    if release is None:
        print("No desktop release has been published.")
        return
    print(sync_mirror(release, args.output))


if __name__ == "__main__":
    main()
