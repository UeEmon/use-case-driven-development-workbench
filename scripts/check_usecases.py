#!/usr/bin/env python3
"""ユースケースの整合性チェックとトレーサビリティ表の生成。

  python scripts/check_usecases.py          # チェックのみ（CI用、問題があれば exit 1）
  python scripts/check_usecases.py --write  # docs/traceability.md を更新
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UC_DIR = ROOT / "docs" / "usecases"
TRACE_MD = ROOT / "docs" / "traceability.md"
MKDOCS_YML = ROOT / "mkdocs.yml"
FEATURE_DIR = ROOT / "tests" / "acceptance"

REQUIRED_KEYS = ["id", "name", "actor", "status", "tests"]
STATUSES = ["記述中", "記述完了", "ロバストネス完了", "シーケンス完了", "実装済"]
ID_RE = re.compile(r"^UC-\d{3}$")


def load_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def repo_url() -> str:
    for line in MKDOCS_YML.read_text(encoding="utf-8").splitlines():
        if line.startswith("repo_url:"):
            return line.split(":", 1)[1].split("#")[0].strip().rstrip("/")
    return ""


def main() -> int:
    errors: list[str] = []
    usecases: list[tuple[dict, Path]] = []
    seen: dict[str, Path] = {}

    for path in sorted(UC_DIR.glob("UC-*.md")):
        fm = load_front_matter(path)
        rel = path.relative_to(ROOT)
        missing = [k for k in REQUIRED_KEYS if not fm.get(k)]
        if missing:
            errors.append(f"{rel}: front matter に {missing} がありません")
            continue
        uc_id = str(fm["id"])
        if not ID_RE.match(uc_id):
            errors.append(f"{rel}: id '{uc_id}' は UC-000 形式にしてください")
        if not path.name.startswith(uc_id + "-"):
            errors.append(f"{rel}: ファイル名は '{uc_id}-' で始めてください")
        if uc_id in seen:
            errors.append(f"{rel}: id {uc_id} が {seen[uc_id].relative_to(ROOT)} と重複")
        seen[uc_id] = path
        if fm["status"] not in STATUSES:
            errors.append(f"{rel}: status は {STATUSES} のいずれか")
        body = path.read_text(encoding="utf-8")
        for section in ("## 基本コース", "## 代替コース"):
            if section not in body:
                errors.append(f"{rel}: '{section}' セクションがありません")
        if fm["status"] in STATUSES and STATUSES.index(fm["status"]) >= 2:
            if "## ロバストネス図" not in body or "@startuml" not in body:
                errors.append(f"{rel}: status={fm['status']} ですがロバストネス図がありません")
        test_path = ROOT / fm["tests"]
        if not test_path.exists():
            errors.append(f"{rel}: 受け入れテスト {fm['tests']} がありません")
        elif f"@{uc_id}" not in test_path.read_text(encoding="utf-8"):
            errors.append(f"{fm['tests']}: Feature に @{uc_id} タグを付けてください")
        usecases.append((fm, path))

    # どのユースケースにも紐づかないテストを検出
    for feature in sorted(FEATURE_DIR.glob("*.feature")):
        tags = set(re.findall(r"@(UC-\d{3})", feature.read_text(encoding="utf-8")))
        for tag in tags - seen.keys():
            errors.append(f"{feature.relative_to(ROOT)}: @{tag} に対応するユースケースがありません")

    if "--write" in sys.argv:
        url = repo_url()
        rows = ["| ID | ユースケース | アクター | 状態 | Issue | 受け入れテスト |",
                "|---|---|---|---|---|---|"]
        for fm, path in usecases:
            issue = fm.get("issue")
            issue_cell = f"[#{issue}]({url}/issues/{issue})" if isinstance(issue, int) and url else "-"
            test_cell = f"[{Path(fm['tests']).name}]({url}/blob/main/{fm['tests']})" if url else fm["tests"]
            rows.append(f"| [{fm['id']}](usecases/{path.name}) | {fm['name']} | {fm['actor']} "
                        f"| {fm['status']} | {issue_cell} | {test_cell} |")
        text = TRACE_MD.read_text(encoding="utf-8")
        text = re.sub(r"(<!-- TRACE:START -->\n).*?(<!-- TRACE:END -->)",
                      lambda m: m.group(1) + "\n".join(rows) + "\n" + m.group(2), text, flags=re.S)
        TRACE_MD.write_text(text, encoding="utf-8")
        print(f"updated {TRACE_MD.relative_to(ROOT)}")

    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(usecases)} use cases checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
