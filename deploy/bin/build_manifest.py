#!/usr/bin/env python3
"""Prepare an immutable signed update manifest with an offline signing identity."""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import file_digest, sha256
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc_text(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def manifest(policy, keys, assets, now):
    if policy["epoch"] != keys["epoch"]:
        raise ValueError("Manifest epoch does not match the signed key directory")
    key, = [key for key in keys["keys"] if key["id"] == policy["key_id"]]
    expires = min(now + timedelta(days=60), datetime.fromisoformat(key["expires_at"]))
    if expires <= now or policy["version"] < 1:
        raise ValueError("Expired key or invalid manifest version")
    packages = {}
    for kind, name in policy["packages"].items():
        resolved = (assets / name).resolve()
        if not resolved.is_relative_to(assets):
            raise ValueError(f"Package outside the artifact: {kind}")
        with resolved.open("rb") as file:
            checksum = file_digest(file, "sha256").hexdigest()
        packages[kind] = {"path": name, "sha256": checksum, "size": resolved.stat().st_size}
    result = {"schema": "qunxing.manifest/1",
              "epoch": policy["epoch"], "version": policy["version"], "key_id": key["id"],
              "generated_at": utc_text(now), "expires_at": utc_text(expires),
              "min_app_version": policy["min_app_version"],
              "mirrors": policy["mirrors"], "inbox_endpoints": policy["inbox_endpoints"],
              "packages": packages}
    return result, key["public_key"]


def sign(args):
    subprocess.run(["minisign", "-Vm", str(args.keys), "-p", str(args.root_public)], check=True)
    policy, keys = read_json(args.policy), read_json(args.keys)
    assets = args.assets.resolve()
    if args.signing_identity.resolve().is_relative_to(assets):
        raise ValueError("Keep the signing identity outside the artifact")
    result, public_key = manifest(policy, keys, assets, datetime.now(timezone.utc))
    if args.previous:
        previous = read_json(args.previous)
        if (result["epoch"], result["version"]) <= (previous["epoch"], previous["version"]):
            raise ValueError("Manifest epoch or version is not newer")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qx-manifest-", dir=args.output.parent) as temp:
        stage = Path(temp)/"update"
        stage.mkdir()
        name = stage/"manifest.json"
        name.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        existing_log = args.previous.with_name("manifests.log") if args.previous else None
        history = existing_log.read_text(encoding="utf-8").splitlines() if existing_log else []
        log_entry = {field: result[field] for field in ("epoch", "version", "key_id", "generated_at")}
        log_entry["sha256"] = sha256(name.read_bytes()).hexdigest()
        (stage/"manifests.log").write_text("\n".join(history + [json.dumps(log_entry, separators=(",", ":"))]) + "\n",
                                         encoding="utf-8", newline="\n")
        comment = f'version={result["version"]} epoch={result["epoch"]} expires_at={result["expires_at"]}'
        subprocess.run(["minisign", "-Sm", str(name), "-s", str(args.signing_identity), "-t", comment], check=True)
        subprocess.run(["minisign", "-Vm", str(name), "-P", public_key], check=True)
        shutil.copy2(args.keys, stage/"keys.json")
        shutil.copy2(args.keys.with_suffix(args.keys.suffix + ".minisig"), stage/"keys.json.minisig")
        stage.rename(args.output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("policy", "keys", "root-public", "signing-identity", "assets", "output"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    sign(parser.parse_args())


if __name__ == "__main__":
    main()
