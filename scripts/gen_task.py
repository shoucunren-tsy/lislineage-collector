#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成采集任务包。

用法:
    python scripts/gen_task.py --out "工作夹/B01_张三" --batch B01 --collector 张三 \
        --scholars fenghuiling:冯惠玲,huchangping:胡昌平

产物:
    B01_张三/
    ├── TASK.md
    └── <scholar_id>/
        ├── 10 张 CSV（含表头）
        ├── manifest.json
        ├── report.md
        └── evidence/
"""

import argparse
import csv
import json
import re
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

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "fields.json"
TEMPLATES = ROOT / "templates"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


def load_schema():
    if not SCHEMA_PATH.exists():
        sys.exit("找不到字段契约: %s" % SCHEMA_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def parse_scholars(raw):
    scholars = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            sid, name = item.split(":", 1)
        elif "：" in item:
            sid, name = item.split("：", 1)
        else:
            sys.exit("学者参数格式应为 学者ID:姓名，实际: %s" % item)
        sid, name = sid.strip(), name.strip()
        if not ID_RE.fullmatch(sid):
            sys.exit("学者ID不合法: %s（要求小写字母开头，2-31 位英文数字下划线）" % sid)
        if not name:
            sys.exit("学者姓名不能为空: %s" % item)
        scholars.append((sid, name))
    if not scholars:
        sys.exit("至少指定一位学者")
    ids = [s for s, _ in scholars]
    if len(ids) != len(set(ids)):
        sys.exit("学者ID重复")
    return scholars


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def render(template_text, mapping):
    for key, value in mapping.items():
        template_text = template_text.replace("{{%s}}" % key, value)
    return template_text


def main():
    parser = argparse.ArgumentParser(description="生成图情谱系采集任务包")
    parser.add_argument("--out", required=True, help="输出目录，按本机习惯自定，如 工作夹/B01_张三")
    parser.add_argument("--batch", required=True, help="批次号，如 B01")
    parser.add_argument("--collector", required=True, help="采集人姓名或代号")
    parser.add_argument("--scholars", required=True,
                        help="学者列表，格式 学者ID:姓名，多个用逗号分隔")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的文件")
    args = parser.parse_args()

    schema = load_schema()
    scholars = parse_scholars(args.scholars)
    out = Path(args.out).expanduser().resolve()
    today = date.today().isoformat()

    out.mkdir(parents=True, exist_ok=True)

    for sid, name in scholars:
        sdir = out / sid
        sdir.mkdir(exist_ok=True)
        (sdir / "evidence").mkdir(exist_ok=True)

        # CSV 表头
        for fname, spec in schema["files"].items():
            if spec["kind"] != "csv":
                continue
            path = sdir / fname
            if path.exists() and not args.force:
                continue
            columns = [c["name"] for c in spec["columns"]]
            rows = []
            if fname == "profile.csv":
                row = {c: "" for c in columns}
                row["scholar_id"] = sid
                row["name_cn"] = name
                rows.append([row[c] for c in columns])
            write_csv(path, columns, rows)

        # manifest
        mpath = sdir / "manifest.json"
        if not mpath.exists() or args.force:
            manifest = {
                "contract_version": schema["contract_version"],
                "batch": args.batch,
                "collector": args.collector,
                "scholar_id": sid,
                "scholar_name": name,
                "submitted_at": today,
                "coverage": {k: "C" for k in schema["manifest"]["coverage_keys"]},
                "boundaries": ["待填写：写清实际受限的渠道与未覆盖范围"],
                "gaps": [],
                "files": [],
            }
            mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

        # report
        rpath = sdir / "report.md"
        if not rpath.exists() or args.force:
            template = (TEMPLATES / "report.md").read_text(encoding="utf-8")
            rpath.write_text(render(template, {
                "学者姓名": name,
                "采集人": args.collector,
                "批次": args.batch,
                "提交日期": today,
            }), encoding="utf-8")

    # 批次 TASK
    task_path = out / "TASK.md"
    if not task_path.exists() or args.force:
        template = (TEMPLATES / "TASK.md").read_text(encoding="utf-8")
        task_path.write_text(render(template, {
            "学者姓名": "、".join(name for _, name in scholars),
            "scholar_id": "、".join(sid for sid, _ in scholars),
            "batch": args.batch,
            "collector": args.collector,
            "生成日期": today,
            "contract_version": schema["contract_version"],
        }), encoding="utf-8")

    print("任务包已生成: %s" % out)
    print("采集人: %s · 批次: %s · 学者 %d 位" % (args.collector, args.batch, len(scholars)))
    for sid, name in scholars:
        print("  - %s (%s)" % (name, sid))
    print("\n下一步: 按 TASK.md 采集，完成后运行")
    print('  python scripts/validate_package.py "%s"' % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
