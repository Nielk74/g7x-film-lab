#!/usr/bin/env python3
"""Build a deterministic, no-code installation ZIP from reviewed release files."""
from pathlib import Path
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"


def package():
    tag = os.environ.get("RELEASE_TAG", "v" + VERSION)
    if tag != "v" + VERSION:
        raise ValueError("Release tag does not match package version")
    manifest = json.loads((ROOT / "research/bake-manifest.json").read_text())
    assert manifest["version"] == VERSION and len(manifest["looks"]) == 5
    paths = [ROOT / name for name in ["START-HERE.html", "OPEN-ME.command", "OPEN-ME.bat", "README.md", "LICENSE", "DATA-LICENSE.md", "CHANGELOG.txt"]]
    for folder in ["profiles", "luts", "previews", "examples", "docs", "licenses", "research"]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.name != ".DS_Store")
    paths = sorted(set(paths))
    assert all(p.exists() for p in paths)
    checksums = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(ROOT).as_posix() + "\n" for p in paths)
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    target = output / f"G7X-Film-Lab-{VERSION}.zip"
    prefix = f"G7X-Film-Lab-{VERSION}/"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(prefix + name, date_time=(2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith(".command") else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo(prefix + "SHA256SUMS", date_time=(2026, 11, 12, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, checksums.encode())
    (output / "SHA256SUMS").write_text(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + target.name + "\n")
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert len([x for x in archive.namelist() if x.endswith(".PF3")]) == 5
        assert len([x for x in archive.namelist() if x.endswith(".cube")]) == 5
        assert not any(x.endswith((".FIR", ".CR3", ".pkg", ".dmg", ".dll", ".dylib")) for x in archive.namelist())
    print(target.name, target.stat().st_size, "bytes")


if __name__ == "__main__": package()
