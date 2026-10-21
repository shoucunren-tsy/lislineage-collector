#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图情谱系采集包校验器。

用法:
    python scripts/validate_package.py <批次目录或单学者目录> [--strict] [--json]

检查项:
    目录结构 / CSV 编码与表头 / 必填与枚举 / source_id 引用 /
    论文作者归属 / 被引状态一致性 / 履历来源等级 / 审计闭合 /
    覆盖等级一致性 / 绝对化表述 / 摘录与快照比对

只依赖 Python 标准库，Python 3.9+。
"""

import argparse
import csv
import hashlib
import html
import io
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

LEVEL_ERROR = "错误"
LEVEL_WARN = "警告"


class Issues:
    def __init__(self):
        self.items = []

    def add(self, level, file, row, field, message):
        self.items.append({
            "level": level,
            "file": file,
            "row": row,
            "field": field,
            "message": message,
        })

    def error(self, file, row, field, message):
        self.add(LEVEL_ERROR, file, row, field, message)

    def warn(self, file, row, field, message):
        self.add(LEVEL_WARN, file, row, field, message)

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)


def load_schema():
    if not SCHEMA_PATH.exists():
        sys.exit("找不到字段契约: %s" % SCHEMA_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------- 通用小工具 ----------

DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
SOURCE_ID_RE = re.compile(r"^S\d{3,}$", re.IGNORECASE)
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$")


def is_int(value):
    return bool(re.fullmatch(r"\d+", value.strip()))


def valid_date(value, allow_until=False):
    value = value.strip()
    if allow_until and value == "至今":
        return True
    if not DATE_RE.fullmatch(value):
        return False
    parts = value.split("-")
    try:
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 1
        d = int(parts[2]) if len(parts) > 2 else 1
        date(y, m, d)
    except ValueError:
        return False
    return 1900 <= y <= 2100


def date_key(value):
    """把 YYYY / YYYY-MM / YYYY-MM-DD / 至今 转成可比较元组。"""
    if value.strip() == "至今":
        return (9999, 12, 31)
    parts = [int(p) for p in value.split("-")]
    while len(parts) < 3:
        parts.append(12 if len(parts) == 1 else 31)
    return tuple(parts)


def norm_text(value):
    return re.sub(r"\s+", "", value or "").lower()


def norm_name(value):
    return re.sub(r"[\s\.\-·,，、;；:：'\"()（）]", "", value or "").lower()


def strip_tags(text):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html.unescape(text)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- CSV 读取 ----------

def read_csv(path, expected_columns, issues, label):
    """返回 [(逻辑行号, dict)]。表头/编码问题记入 issues。"""
    try:
        raw = path.read_bytes()
    except OSError as e:
        issues.error(label, 0, "", "无法读取: %s" % e)
        return []

    if not raw.strip():
        issues.error(label, 0, "", "空文件（至少保留表头）")
        return []

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            raw.decode("gbk")
            issues.error(label, 0, "", "编码不是 UTF-8（疑似 GBK）。请另存为「CSV UTF-8」")
        except UnicodeDecodeError:
            issues.error(label, 0, "", "无法识别编码，请另存为 UTF-8")
        return []

    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as e:
        issues.error(label, 0, "", "CSV 解析失败: %s" % e)
        return []

    if not rows:
        issues.error(label, 0, "", "文件没有内容")
        return []

    header = [h.strip() for h in rows[0]]
    if header != expected_columns:
        missing = [c for c in expected_columns if c not in header]
        extra = [c for c in header if c not in expected_columns]
        detail = []
        if missing:
            detail.append("缺少列: %s" % ", ".join(missing))
        if extra:
            detail.append("多余列: %s" % ", ".join(extra))
        if not missing and not extra:
            detail.append("列顺序被改动")
        issues.error(label, 1, "", "表头与契约不一致；%s" % "；".join(detail))
        # 尽量按列名取值，保证后续检查还能跑
        index = {name: i for i, name in enumerate(header)}
    else:
        index = {name: i for i, name in enumerate(expected_columns)}

    data = []
    for logical_row, raw_row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in raw_row):
            continue
        if len(raw_row) > len(header) and any(c.strip() for c in raw_row[len(header):]):
            issues.warn(label, logical_row, "", "该行超出表头的列有内容，可能多写了逗号")
        values = []
        for name in expected_columns:
            i = index.get(name)
            values.append(raw_row[i].strip() if i is not None and i < len(raw_row) else "")
        data.append((logical_row, dict(zip(expected_columns, values))))
    return data


# ---------- 学者目录校验 ----------

class ScholarValidator:
    def __init__(self, directory, schema, skip_hashes=False):
        self.dir = directory
        self.schema = schema
        # pack.py 重算哈希时必须跳过旧哈希，否则改完文件就永远无法重新打包
        self.skip_hashes = skip_hashes
        self.issues = Issues()
        self.tables = {}
        self.manifest = {}
        self.source_tiers = {}
        self.source_snapshots = {}
        self.names = set()

    # -- 入口 --
    def run(self):
        self.check_structure()
        if not self.manifest:
            self.load_manifest()
        self.load_tables()
        self.check_profile()
        self.check_sources()
        self.check_scholar_ids()
        self.check_required_and_enums()
        self.check_source_refs()
        self.check_papers()
        self.check_career()
        self.check_activities()
        self.check_relations()
        self.check_books()
        self.check_rejects()
        self.check_audit()
        self.check_coverage()
        self.check_manifest_files()
        self.check_report()
        self.check_excerpts_against_snapshots()
        self.check_forbidden_claims()
        return self.issues.items

    # -- 结构 --
    def check_structure(self):
        required = self.schema["required_files"]
        for name in required:
            p = self.dir / name
            if not p.exists():
                self.issues.error(name, 0, "", "缺少必需文件/目录")
        evidence = self.dir / "evidence"
        if evidence.exists() and not evidence.is_dir():
            self.issues.error("evidence", 0, "", "应为目录")

    def load_manifest(self):
        path = self.dir / "manifest.json"
        if not path.exists():
            return
        try:
            self.manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as e:
            self.issues.error("manifest.json", 0, "", "JSON 解析失败: %s" % e)
            self.manifest = {}
            return

        spec = self.schema["manifest"]
        for key in spec["required_keys"]:
            if key not in self.manifest:
                self.issues.error("manifest.json", 0, key, "缺少字段")
        if self.manifest.get("contract_version") not in (None, self.schema["contract_version"]):
            self.issues.warn("manifest.json", 0, "contract_version",
                             "契约版本为 %s，当前为 %s" % (self.manifest.get("contract_version"),
                                                        self.schema["contract_version"]))

        sid = self.manifest.get("scholar_id", "")
        if sid and sid != self.dir.name:
            self.issues.error("manifest.json", 0, "scholar_id",
                              "与文件夹名不一致（%s != %s）" % (sid, self.dir.name))
        if not sid:
            self.issues.error("manifest.json", 0, "scholar_id", "必填")
        elif not ID_RE.fullmatch(sid):
            self.issues.error("manifest.json", 0, "scholar_id",
                              "格式不合法，应为小写字母开头的英文数字下划线")

        for key in ("batch", "collector", "scholar_name"):
            if self.is_placeholder(self.manifest.get(key, "")):
                self.issues.error("manifest.json", 0, key, "仍为占位内容")

        submitted = str(self.manifest.get("submitted_at", ""))
        if not valid_date(submitted) or len(submitted) != 10:
            self.issues.error("manifest.json", 0, "submitted_at", "应为 YYYY-MM-DD")

        coverage = self.manifest.get("coverage")
        if not isinstance(coverage, dict):
            self.issues.error("manifest.json", 0, "coverage", "应为对象")
            self.manifest["coverage"] = {}
        else:
            for key in spec["coverage_keys"]:
                if key not in coverage:
                    self.issues.error("manifest.json", 0, "coverage", "缺少维度 %s" % key)
                elif coverage[key] not in self.schema["enums"]["coverage_level"]:
                    self.issues.error("manifest.json", 0, "coverage.%s" % key,
                                      "取值应为 A/B/C，实际为 %s" % coverage[key])
            for key in coverage:
                if key not in spec["coverage_keys"]:
                    self.issues.warn("manifest.json", 0, "coverage", "未知维度 %s" % key)

        boundaries = self.manifest.get("boundaries")
        if not isinstance(boundaries, list) or not boundaries:
            self.issues.error("manifest.json", 0, "boundaries", "至少写 1 条边界，不能为空")
        else:
            for i, item in enumerate(boundaries, 1):
                if not isinstance(item, str) or len(item.strip()) < 8:
                    self.issues.error("manifest.json", 0, "boundaries[%d]" % i,
                                      "内容过短或为空")
                elif self.is_placeholder(item):
                    self.issues.error("manifest.json", 0, "boundaries[%d]" % i,
                                      "仍为占位内容")

        gaps = self.manifest.get("gaps")
        if not isinstance(gaps, list):
            self.issues.error("manifest.json", 0, "gaps", "应为数组（可为空）")

        files = self.manifest.get("files")
        if not isinstance(files, list):
            self.issues.error("manifest.json", 0, "files", "应为数组")
            self.manifest["files"] = []

    def load_tables(self):
        for fname, spec in self.schema["files"].items():
            if spec["kind"] != "csv":
                continue
            path = self.dir / fname
            if not path.exists():
                self.tables[fname] = []
                continue
            columns = [c["name"] for c in spec["columns"]]
            self.tables[fname] = read_csv(path, columns, self.issues, fname)

    # -- profile --
    def check_profile(self):
        rows = self.tables.get("profile.csv", [])
        if len(rows) != 1:
            self.issues.error("profile.csv", 0, "",
                              "必须有且只有 1 行数据，实际 %d 行" % len(rows))
            if not rows:
                return
        _, profile = rows[0]
        if profile.get("scholar_id") != self.dir.name:
            self.issues.error("profile.csv", 2, "scholar_id",
                              "必须等于文件夹名 %s" % self.dir.name)
        self.names = {profile.get("name_cn", ""), profile.get("name_en", "")}
        for variant in re.split(r"[|、;；]", profile.get("name_variants", "")):
            self.names.add(variant.strip())
        self.names = {n for n in self.names if n}

        orcid = profile.get("orcid", "")
        if orcid and not ORCID_RE.fullmatch(orcid):
            self.issues.warn("profile.csv", 2, "orcid", "格式不符合 0000-0000-0000-000X")
        for col in ("homepage",):
            value = profile.get(col, "")
            if value and not URL_RE.match(value):
                self.issues.warn("profile.csv", 2, col, "不是 http/https URL")

    # -- sources --
    def check_sources(self):
        rows = self.tables.get("sources.csv", [])
        seen = set()
        for row_no, row in rows:
            sid = row["source_id"]
            if not SOURCE_ID_RE.fullmatch(sid):
                self.issues.error("sources.csv", row_no, "source_id",
                                  "应为 S001 这类编号，实际 %s" % sid)
            if sid in seen:
                self.issues.error("sources.csv", row_no, "source_id", "编号重复")
            seen.add(sid)
            self.source_tiers[sid] = row["source_tier"]
            if row.get("snapshot"):
                snap = self.dir / row["snapshot"]
                if not snap.exists():
                    self.issues.error("sources.csv", row_no, "snapshot",
                                      "快照文件不存在: %s" % row["snapshot"])
                else:
                    self.source_snapshots[sid] = snap
            url = row.get("url", "")
            if url and not URL_RE.match(url):
                self.issues.warn("sources.csv", row_no, "url", "不是 http/https URL")
            if row.get("accessed_at") and not valid_date(row["accessed_at"]):
                self.issues.error("sources.csv", row_no, "accessed_at",
                                  "应为 YYYY-MM-DD")

    # -- scholar_id 一致性 --
    def check_scholar_ids(self):
        for fname in ("career.csv", "papers_cn.csv", "papers_intl.csv",
                      "activities.csv", "relations.csv", "books.csv",
                      "rejects.csv", "audit.csv"):
            for row_no, row in self.tables.get(fname, []):
                if row.get("scholar_id") != self.dir.name:
                    self.issues.error(fname, row_no, "scholar_id",
                                      "必须等于文件夹名 %s，实际 %s"
                                      % (self.dir.name, row.get("scholar_id", "")))

    # -- 必填与枚举 --
    def check_required_and_enums(self):
        special = {
            ("career.csv", "source_id"), ("career.csv", "excerpt"),
            ("papers_cn.csv", "year"), ("papers_intl.csv", "year"),
        }
        enums = self.schema["enums"]
        for fname, spec in self.schema["files"].items():
            if spec["kind"] != "csv":
                continue
            for row_no, row in self.tables.get(fname, []):
                for col in spec["columns"]:
                    name = col["name"]
                    value = row.get(name, "")
                    if col.get("required") and not value and (fname, name) not in special:
                        self.issues.error(fname, row_no, name, "必填字段为空")
                    if value and col.get("enum"):
                        allowed = enums[col["enum"]]
                        if value not in allowed:
                            self.issues.error(fname, row_no, name,
                                              "取值不合法：%s（允许 %s）"
                                              % (value, "/".join(allowed)))

    # -- source_id 引用 --
    def check_source_refs(self):
        used = set()
        for fname in ("career.csv", "papers_cn.csv", "papers_intl.csv",
                      "activities.csv", "relations.csv", "books.csv"):
            for row_no, row in self.tables.get(fname, []):
                sid = row.get("source_id", "")
                if not sid:
                    continue
                used.add(sid)
                if sid not in self.source_tiers:
                    self.issues.error(fname, row_no, "source_id",
                                      "来源表中不存在 %s" % sid)
        for sid in sorted(set(self.source_tiers) - used):
            self.issues.warn("sources.csv", 0, sid, "来源已登记但未被任何记录引用")

    # -- 论文 --
    def check_papers(self):
        seen_titles = {}
        for fname in ("papers_cn.csv", "papers_intl.csv"):
            for row_no, row in self.tables.get(fname, []):
                self.check_one_paper(fname, row_no, row)
                key = (norm_text(row.get("title", "")), row.get("year", ""))
                if key[0]:
                    if key in seen_titles:
                        self.issues.error(fname, row_no, "title",
                                          "与本包 %s 第 %d 行重复（同题同年）"
                                          % (seen_titles[key][0], seen_titles[key][1]))
                    else:
                        seen_titles[key] = (fname, row_no)

    def check_one_paper(self, fname, row_no, row):
        year = row.get("year", "")
        notes = row.get("notes", "")
        if not year:
            if not re.match(r"^缺年[:：]", notes):
                self.issues.error(fname, row_no, "year",
                                  "必填；确实无年份时请在 notes 以「缺年:」开头说明")
        elif not (re.fullmatch(r"\d{4}", year) and 1900 <= int(year) <= date.today().year + 1):
            self.issues.error(fname, row_no, "year", "应为四位年份")

        doi = row.get("doi", "")
        if doi and not DOI_RE.match(doi):
            self.issues.warn(fname, row_no, "doi", "不像标准 DOI（应以 10. 开头）")

        authors = row.get("authors", "")
        if not self.authors_contain_scholar(authors):
            self.issues.error(fname, row_no, "authors",
                              "作者列表中没有本学者，请核对归属；若是姓名写法差异，补进 profile.name_variants")

        if row.get("action") == "correction" and len(row.get("notes", "")) < 4:
            self.issues.warn(fname, row_no, "notes", "action=correction 应在 notes 说明订正内容")

        status = row.get("cited_status", "")
        cited = row.get("cited", "")
        if status in ("unknown", "blocked"):
            if cited:
                self.issues.error(fname, row_no, "cited",
                                  "状态为 %s 时必须留空，不能写 %s" % (status, cited))
        elif status in ("verified", "recorded_value", "verified_zero"):
            if not is_int(cited):
                self.issues.error(fname, row_no, "cited",
                                  "状态为 %s 时必须是整数" % status)
            elif status == "verified_zero" and cited != "0":
                self.issues.error(fname, row_no, "cited",
                                  "verified_zero 必须为 0")
            elif status != "verified_zero" and cited == "0":
                self.issues.error(fname, row_no, "cited",
                                  "0 只能用于 verified_zero（页面明确显示 0）")
            if not row.get("cited_source"):
                self.issues.error(fname, row_no, "cited_source",
                                  "有被引数值时必须写数据来源")
            if not row.get("cited_date") or not valid_date(row["cited_date"]):
                self.issues.error(fname, row_no, "cited_date", "应为 YYYY-MM-DD")
            elif not row.get("cited_url"):
                self.issues.warn(fname, row_no, "cited_url", "建议补充被引页面 URL")

    def authors_contain_scholar(self, authors):
        if not authors:
            return False
        tokens = [norm_name(t) for t in re.split(r"[|;；]", authors) if t.strip()]
        for name in self.names:
            nn = norm_name(name)
            if not nn:
                continue
            for token in tokens:
                token = token.rstrip("等")
                if token == nn:
                    return True
            # 英文姓名顺序可能相反，允许整体子串匹配
            if re.search(r"[a-z]", nn) and nn in norm_name(authors):
                return True
        return False

    # -- 履历 --
    def check_career(self):
        rows = self.tables.get("career.csv", [])
        for row_no, row in rows:
            status = row.get("status", "")
            if status == "unknown":
                if not row.get("notes"):
                    self.issues.warn("career.csv", row_no, "notes",
                                     "status=unknown 应说明查过哪些渠道")
            else:
                if not row.get("source_id"):
                    self.issues.error("career.csv", row_no, "source_id", "必填")
                if not row.get("excerpt") or len(row["excerpt"]) < 6:
                    self.issues.error("career.csv", row_no, "excerpt",
                                      "必填，且至少 6 个字符")
                tier = self.source_tiers.get(row.get("source_id", ""))
                if status == "confirmed" and tier == "二手":
                    self.issues.warn("career.csv", row_no, "status",
                                     "confirmed 只依据二手来源，建议降为 candidate 或补一手来源")
            start, end = row.get("start", ""), row.get("end", "")
            for col, value in (("start", start), ("end", end)):
                if value and not valid_date(value, allow_until=True):
                    self.issues.error("career.csv", row_no, col,
                                      "格式应为 YYYY / YYYY-MM / YYYY-MM-DD / 至今")
            if start and end and valid_date(start) and valid_date(end, allow_until=True):
                if date_key(start) > date_key(end):
                    self.issues.error("career.csv", row_no, "start", "开始时间晚于结束时间")

    # -- 活动 --
    def check_activities(self):
        for row_no, row in self.tables.get("activities.csv", []):
            if row.get("date") and not valid_date(row["date"]):
                self.issues.error("activities.csv", row_no, "date",
                                  "格式应为 YYYY-MM-DD，可降级到月/年")
            if row.get("article_url") and not URL_RE.match(row["article_url"]):
                self.issues.warn("activities.csv", row_no, "article_url", "不是 http/https URL")
            if len(row.get("excerpt", "")) < 6:
                self.issues.error("activities.csv", row_no, "excerpt",
                                  "必填，且至少 6 个字符")

    # -- 关系 --
    def check_relations(self):
        for row_no, row in self.tables.get("relations.csv", []):
            if len(row.get("excerpt", "")) < 6:
                self.issues.error("relations.csv", row_no, "excerpt",
                                  "必填，且至少 6 个字符")
            if row.get("other_scholar_id") and not ID_RE.fullmatch(row["other_scholar_id"]):
                self.issues.warn("relations.csv", row_no, "other_scholar_id",
                                 "格式不像站点 ID")
            for col in ("start", "end"):
                if row.get(col) and not re.fullmatch(r"\d{4}", row[col]):
                    self.issues.warn("relations.csv", row_no, col, "建议只写四位年份")

    # -- 著作 --
    def check_books(self):
        for row_no, row in self.tables.get("books.csv", []):
            year = row.get("year", "")
            if year and not (re.fullmatch(r"\d{4}", year) and 1800 <= int(year) <= date.today().year + 1):
                self.issues.error("books.csv", row_no, "year", "应为四位年份")
            if len(row.get("excerpt", "")) < 6:
                self.issues.error("books.csv", row_no, "excerpt",
                                  "必填，且至少 6 个字符")

    # -- 排除项 --
    def check_rejects(self):
        for row_no, row in self.tables.get("rejects.csv", []):
            if len(row.get("reason", "")) < 2:
                self.issues.error("rejects.csv", row_no, "reason", "必填")
            if len(row.get("evidence", "")) < 4:
                self.issues.error("rejects.csv", row_no, "evidence", "必填，写排除依据")
            if row.get("status") == "pending" and not row.get("notes"):
                self.issues.warn("rejects.csv", row_no, "notes", "pending 项建议写明待核点")

    # -- 审计 --
    def check_audit(self):
        self.audit_dims_closed = set()
        self.audit_dims_open = set()
        for row_no, row in self.tables.get("audit.csv", []):
            for col in ("returned", "unique_ids"):
                if not is_int(row.get(col, "")):
                    self.issues.error("audit.csv", row_no, col, "必须是非负整数")
            total = row.get("total", "")
            if total and not is_int(total):
                self.issues.error("audit.csv", row_no, "total", "必须是整数或留空")
            if row.get("date") and not valid_date(row["date"]):
                self.issues.error("audit.csv", row_no, "date", "应为 YYYY-MM-DD")

            closure = row.get("closure", "")
            dim = row.get("dimension", "")
            if closure == "closed":
                self.audit_dims_closed.add(dim)
                if row.get("last_page") != "true":
                    self.issues.error("audit.csv", row_no, "last_page",
                                      "closed 必须 last_page=true")
                if is_int(row.get("returned", "")) and is_int(row.get("unique_ids", "")):
                    if row["returned"] != row["unique_ids"]:
                        self.issues.error("audit.csv", row_no, "unique_ids",
                                          "closed 要求 returned = unique_ids")
                    if total and total != row["returned"]:
                        self.issues.error("audit.csv", row_no, "total",
                                          "closed 要求 total = returned")
            elif closure == "open":
                self.audit_dims_open.add(dim)
                if len(row.get("note", "")) < 6:
                    self.issues.error("audit.csv", row_no, "note",
                                      "closure=open 必须写明未闭合原因")

    # -- 覆盖等级 --
    def check_coverage(self):
        coverage = self.manifest.get("coverage", {})
        table_of = {
            "papers_cn": "papers_cn.csv",
            "papers_intl": "papers_intl.csv",
            "career": "career.csv",
            "activities": "activities.csv",
            "relations": "relations.csv",
            "books": "books.csv",
        }
        for dim, level in coverage.items():
            if dim not in table_of or level not in ("A", "B"):
                continue
            count = len(self.tables.get(table_of[dim], []))
            if count == 0:
                if level == "A":
                    self.issues.error("manifest.json", 0, "coverage.%s" % dim,
                                      "评为 A 但该维度没有任何记录")
                else:
                    self.issues.warn("manifest.json", 0, "coverage.%s" % dim,
                                     "评为 B 但该维度没有任何记录")
            if level == "A":
                if dim in getattr(self, "audit_dims_open", set()):
                    self.issues.error("manifest.json", 0, "coverage.%s" % dim,
                                      "存在未闭合审计，不能评 A")
                if dim not in getattr(self, "audit_dims_closed", set()):
                    self.issues.error("manifest.json", 0, "coverage.%s" % dim,
                                      "评 A 需要至少一条 closure=closed 的审计")

    # -- manifest.files 哈希 --
    def check_manifest_files(self):
        if self.skip_hashes:
            return
        for entry in self.manifest.get("files", []) or []:
            if not isinstance(entry, dict) or "name" not in entry:
                self.issues.error("manifest.json", 0, "files", "条目缺少 name")
                continue
            path = self.dir / entry["name"]
            if not path.exists():
                self.issues.error("manifest.json", 0, "files",
                                  "文件不存在: %s" % entry["name"])
                continue
            actual = sha256_file(path)
            expected = entry.get("sha256", "")
            if expected and expected != actual:
                self.issues.error("manifest.json", 0, "files",
                                  "%s 哈希不一致，请重新运行 pack.py" % entry["name"])

    # -- 报告 --
    def check_report(self):
        path = self.dir / "report.md"
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if len(text) < 200:
            self.issues.error("report.md", 0, "", "内容过短，至少 200 字")
        if "边界与缺口" not in text:
            self.issues.error("report.md", 0, "", "缺少「边界与缺口」小节")
        if re.search(r"\{\{[^}]+\}\}", text):
            self.issues.error("report.md", 0, "", "仍有 {{占位符}} 未替换")

    # -- 摘录 vs 快照 --
    def check_excerpts_against_snapshots(self):
        if not self.source_snapshots:
            return
        cache = {}
        for fname in ("career.csv", "papers_cn.csv", "papers_intl.csv",
                      "activities.csv", "relations.csv", "books.csv"):
            for row_no, row in self.tables.get(fname, []):
                sid = row.get("source_id", "")
                excerpt = row.get("excerpt", "")
                if not sid or len(excerpt) < 6 or sid not in self.source_snapshots:
                    continue
                snap = self.source_snapshots[sid]
                if snap.suffix.lower() not in (".html", ".htm", ".txt", ".md", ".json", ".xml"):
                    continue
                if sid not in cache:
                    try:
                        raw = snap.read_text(encoding="utf-8-sig", errors="replace")
                        cache[sid] = norm_text(strip_tags(raw))
                    except OSError:
                        cache[sid] = ""
                haystack = cache[sid]
                if haystack and norm_text(excerpt) not in haystack:
                    self.issues.warn(fname, row_no, "excerpt",
                                     "摘录未在快照 %s 中找到（快照可能只含首屏，或摘录非逐字）"
                                     % snap.name)

    # -- 绝对化表述 --
    def check_forbidden_claims(self):
        phrases = sorted(self.schema["forbidden_claims"], key=len, reverse=True)
        negations = self.schema["negation_markers"]

        def scan(text, file, row, field):
            mask = [False] * len(text)
            for phrase in phrases:
                start = 0
                while True:
                    idx = text.find(phrase, start)
                    if idx < 0:
                        break
                    end = idx + len(phrase)
                    if any(mask[idx:end]):
                        start = end
                        continue
                    # 只看同一句/同一单元格；否则上一行的「未取到」会误救下一行的「全部收齐」
                    prefix = re.split(r"[\n\r。！？；;|，,]", text[:idx])[-1][-20:]
                    if not any(neg in prefix for neg in negations):
                        self.issues.error(file, row, field,
                                          "出现绝对化表述「%s」，请改写为有边界的描述" % phrase)
                    for i in range(idx, end):
                        mask[i] = True
                    start = end

        for row_no, row in self.tables.get("profile.csv", []):
            scan(row.get("intro_zh", ""), "profile.csv", row_no, "intro_zh")
        for fname, spec in self.schema["files"].items():
            if spec["kind"] != "csv":
                continue
            for row_no, row in self.tables.get(fname, []):
                if "notes" in row:
                    scan(row.get("notes", ""), fname, row_no, "notes")
        report = self.dir / "report.md"
        if report.exists():
            scan(report.read_text(encoding="utf-8-sig", errors="replace"), "report.md", 0, "")
        for i, item in enumerate(self.manifest.get("boundaries", []) or [], 1):
            if isinstance(item, str):
                scan(item, "manifest.json", 0, "boundaries[%d]" % i)

    @staticmethod
    def is_placeholder(value):
        if not isinstance(value, str):
            return False
        placeholders = ["待填写", "TODO", "todo", "xxx", "XXX", "示例填写", "待补"]
        return any(p in value for p in placeholders)


# ---------- 批次扫描 ----------

def find_scholar_dirs(root):
    if (root / "manifest.json").exists() or (root / "profile.csv").exists():
        return [root]
    dirs = sorted({p.parent for p in root.rglob("profile.csv")
                   if (p.parent / "manifest.json").exists()})
    return dirs


def main():
    parser = argparse.ArgumentParser(description="校验图情谱系采集数据包")
    parser.add_argument("path", help="批次目录或单个学者目录")
    parser.add_argument("--strict", action="store_true", help="把警告也视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print("路径不存在: %s" % root)
        return 2

    schema = load_schema()
    scholar_dirs = find_scholar_dirs(root)
    if not scholar_dirs:
        print("在 %s 下没有找到含 manifest.json + profile.csv 的学者目录" % root)
        return 2

    all_results = []
    batches = {}
    for d in scholar_dirs:
        validator = ScholarValidator(d, schema)
        items = validator.run()
        all_results.append({
            "scholar": d.name,
            "path": str(d),
            "errors": sum(1 for i in items if i["level"] == LEVEL_ERROR),
            "warnings": sum(1 for i in items if i["level"] == LEVEL_WARN),
            "issues": items,
        })
        m = validator.manifest
        if m.get("batch"):
            batches.setdefault(m["batch"], set()).add(m.get("collector", ""))

    # 批次一致性
    batch_issues = []
    for batch, collectors in batches.items():
        if len(collectors) > 1:
            batch_issues.append("批次 %s 出现多个采集人: %s"
                                % (batch, "、".join(sorted(collectors))))
    scholar_ids = [r["scholar"] for r in all_results]
    dupes = {x for x in scholar_ids if scholar_ids.count(x) > 1}
    for dupe in dupes:
        batch_issues.append("学者目录重名: %s" % dupe)

    total_errors = sum(r["errors"] for r in all_results) + len(batch_issues)
    total_warnings = sum(r["warnings"] for r in all_results)
    passed = total_errors == 0 and (not args.strict or total_warnings == 0)

    if args.json:
        print(json.dumps({
            "root": str(root),
            "passed": passed,
            "errors": total_errors,
            "warnings": total_warnings,
            "scholars": all_results,
            "batch_issues": batch_issues,
        }, ensure_ascii=False, indent=2))
        return 0 if passed else 1

    print("=" * 64)
    print("图情谱系采集包校验")
    print("路径: %s" % root)
    print("学者: %d 位" % len(all_results))
    print("=" * 64)
    for r in all_results:
        print("\n[%s] 错误 %d · 警告 %d" % (r["scholar"], r["errors"], r["warnings"]))
        for issue in r["issues"]:
            loc = issue["file"]
            if issue["row"]:
                loc += " 第%d行" % issue["row"]
            if issue["field"]:
                loc += " · " + issue["field"]
            print("  [%s] %s: %s" % (issue["level"], loc, issue["message"]))
    if batch_issues:
        print("\n[批次一致性]")
        for msg in batch_issues:
            print("  [错误] %s" % msg)

    print("\n" + "-" * 64)
    print("合计: 错误 %d · 警告 %d" % (total_errors, total_warnings))
    if passed:
        print("结果: 通过" + ("（strict）" if args.strict else ""))
    else:
        print("结果: 未通过" + ("（含警告）" if args.strict and total_errors == 0 else ""))
    print("-" * 64)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
