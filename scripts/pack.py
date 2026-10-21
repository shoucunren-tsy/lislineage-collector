#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验并生成文件哈希清单。

用法:
    python scripts/pack.py "工作夹/B01_张三" [--force]

动作:
    1. 运行校验器；有错误则中止（--force 可跳过）
    2. 把 manifest.submitted_at 更新为打包当天
    3. 把每个学者目录下所有文件写入 manifest.files（含 sha256 与行数）
    4. 在批次根目录生成 CHECKSUMS.txt
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path


def _fix_console_encoding():
    """Git Bash 等 UTF-8 终端下，避免中文按 GBK 输出成乱码。"""
    import os
    if sys.platform == "win32" and os.environ.get("MSYSTEM"):
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_fix_console_encoding()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_package import (  # noqa: E402
    SCHEMA_PATH,
    ScholarValidator,
    find_scholar_dirs,
    load_schema,
)

EXCLUDE_NAMES = {"manifest.json", "CHECKSUMS.txt"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path):
    if path.suffix.lower() != ".csv":
        return 0
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        return sum(1 for r in rows[1:] if any(c.strip() for c in r))
    except Exception:
        return 0


def collect_files(sdir):
    files = []
    for path in sorted(sdir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in EXCLUDE_NAMES:
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description="校验并生成采集包哈希清单")
    parser.add_argument("path", help="批次目录或单个学者目录")
    parser.add_argument("--force", action="store_true", help="存在校验错误时仍然打包")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print("路径不存在: %s" % root)
        return 2

    schema = load_schema()
    dirs = find_scholar_dirs(root)
    if not dirs:
        print("没有找到学者目录")
        return 2

    today = date.today().isoformat()
    placeholders = set(schema.get("placeholder_values", []))
    for sdir in dirs:
        mpath = sdir / "manifest.json"
        if not mpath.exists():
            continue
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        value = str(manifest.get("submitted_at") or "").strip()
        if not value or value in placeholders:
            manifest["submitted_at"] = today
            mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    total_errors = 0
    for sdir in dirs:
        validator = ScholarValidator(sdir, schema, skip_hashes=True)
        items = validator.run()
        errors = [i for i in items if i["level"] == "错误"]
        warnings = [i for i in items if i["level"] == "警告"]
        print("[%s] 错误 %d · 警告 %d" % (sdir.name, len(errors), len(warnings)))
        for issue in errors[:20]:
            loc = issue["file"] + (" 第%d行" % issue["row"] if issue["row"] else "")
            print("  [错误] %s: %s" % (loc, issue["message"]))
        if len(errors) > 20:
            print("  …… 其余 %d 条错误请运行 validate_package.py 查看" % (len(errors) - 20))
        total_errors += len(errors)

    if total_errors and not args.force:
        print("\n共有 %d 个错误，已中止。修正后重试，或加 --force 强制打包。" % total_errors)
        return 1

    root_checksums = []
    for sdir in dirs:
        files = collect_files(sdir)
        entries = []
        for path in files:
            rel = path.relative_to(sdir).as_posix()
            entries.append({
                "name": rel,
                "rows": count_rows(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
            root_checksums.append((sdir.name, rel, entries[-1]["sha256"]))

        mpath = sdir / "manifest.json"
        manifest = json.loads(mpath.read_text(encoding="utf-8-sig"))
        manifest["submitted_at"] = today
        manifest["files"] = entries
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
        print("[%s] 已写入 manifest.files：%d 个文件" % (sdir.name, len(entries)))

    sums = root / "CHECKSUMS.txt"
    with open(sums, "w", encoding="utf-8", newline="\n") as f:
        for scholar, rel, digest in root_checksums:
            f.write("%s  %s/%s\n" % (digest, scholar, rel))
    print("哈希清单: %s" % sums)

    if total_errors:
        print("注意: 本次为 --force 打包，仍有 %d 个错误未解决。" % total_errors)
    else:
        print("结果: 已打包")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
