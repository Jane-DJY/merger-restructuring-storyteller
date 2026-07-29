#!/usr/bin/env python3
"""检查并购重组画面数据文件。

脚本读取交易结构画面导出的类 JSON 文本文件，输出上市/挂牌公司、画面状态和
交易步骤核对表。脚本只抽取画面数据本身，不额外推断法律含义。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CODE_LABELS = {
    "son_company": "子公司",
    "shareholder": "股东",
    "controlling_shareholder": "控股股东",
    "actual_shareholder": "实际控制人",
    "trade_stock": "交易股份",
    "assets": "资产",
    "cash": "现金",
}


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    return rtf_to_text(text)


def rtf_to_text(text: str) -> str:
    if not text.lstrip().startswith("{\\rtf"):
        return text

    def replace_hex(match: re.Match[str]) -> str:
        try:
            return bytes.fromhex(match.group(1)).decode("cp1252")
        except Exception:
            return ""

    text = re.sub(r"\\'([0-9a-fA-F]{2})", replace_hex, text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    text = text.replace("{", "").replace("}", "")
    return text


def parse_payload(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidate = stripped[first : last + 1]
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError as error:
            raise SystemExit(f"解析 JSON 画面数据失败：{error}") from error

    raise SystemExit("未在画面数据文件中找到 JSON 对象。")


def as_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise SystemExit("JSON 内容里的 `data` 字段不是对象。")
    return data


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def code_label(value: Any) -> str:
    raw = safe_str(value)
    return CODE_LABELS.get(raw, raw)


def sort_key(stage: dict[str, Any]) -> tuple[int, str]:
    raw = safe_str(stage.get("sort"))
    try:
        return int(raw), raw
    except ValueError:
        return 9999, raw


def format_value(value: Any, unit: Any) -> str:
    raw = safe_str(value)
    unit_text = safe_str(unit)
    if not raw:
        return ""
    if unit_text == "%":
        try:
            number = float(raw)
            if abs(number) <= 1:
                return f"{number * 100:.2f}%"
            return f"{number:.2f}%"
        except ValueError:
            return f"{raw}%"
    if unit_text == "股":
        try:
            return f"{int(float(raw)):,}股"
        except ValueError:
            return f"{raw}股"
    if unit_text:
        return f"{raw}{unit_text}"
    return raw


def compact_trade(trade: dict[str, Any]) -> str:
    org = safe_str(trade.get("org_name")) or "未标明主体"
    org_type = safe_str(trade.get("org_type"))
    subject = safe_str(trade.get("subject_name")) or safe_str(trade.get("type_name")) or "未标明标的"
    type_name = safe_str(trade.get("type_name"))
    ex_type = safe_str(trade.get("ex_type_code"))
    value = format_value(trade.get("value"), trade.get("unit"))

    pieces = [org]
    if org_type:
        pieces.append(f"({code_label(org_type)})")
    pieces.append("—")
    pieces.append(subject)
    if type_name and type_name not in subject:
        pieces.append(f"[{type_name}]")
    if ex_type and ex_type != safe_str(trade.get("type_code")):
        pieces.append(f"({code_label(ex_type)})")
    if value:
        pieces.append(value)
    return " ".join(pieces)


def collect_subjects(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str]] = set()
    rows: list[tuple[str, str, str]] = []
    for state in data.get("assets_info", []) or []:
        status = safe_str(state.get("status"))
        for item in state.get("assets_list", []) or []:
            name = safe_str(item.get("subject_name"))
            role = safe_str(item.get("type_name")) or safe_str(item.get("type_code"))
            value = format_value(item.get("value"), item.get("unit"))
            key = (name, role)
            if name and key not in seen:
                seen.add(key)
                note = f"状态 {status}"
                if value:
                    note += f"，数值 {value}"
                rows.append((name, role, note))
    return rows


def render_markdown(path: Path, data: dict[str, Any]) -> str:
    company = data.get("company_info") or {}
    process = data.get("process") or []
    if not isinstance(process, list):
        process = []
    stages = sorted([s for s in process if isinstance(s, dict)], key=sort_key)

    company_name = safe_str(company.get("name")) or "未识别"
    company_code = safe_str(company.get("code"))
    title_name = f"{company_name}（{company_code}）" if company_code else company_name

    lines: list[str] = []
    lines.append("# 画面数据交易步骤核对")
    lines.append("")
    lines.append(f"- 文件：`{path}`")
    lines.append(f"- 公司：{title_name}")
    lines.append(f"- 画面步骤数量：{len(stages)}")
    lines.append("")
    lines.append("## 步骤总表")
    lines.append("")
    lines.append("| 顺序 | 步骤名称 | 画面描述 |")
    lines.append("|---|---|---|")
    for stage in stages:
        lines.append(
            "| {sort} | {name} | {description} |".format(
                sort=safe_str(stage.get("sort")),
                name=safe_str(stage.get("stage_name")),
                description=safe_str(stage.get("description")).replace("|", "｜"),
            )
        )

    lines.append("")
    lines.append("## 步骤明细")
    for index, stage in enumerate(stages, 1):
        name = safe_str(stage.get("stage_name")) or f"步骤{index}"
        lines.append("")
        lines.append(f"### {index}. {name}")
        description = safe_str(stage.get("description"))
        if description:
            lines.append(f"- 画面描述：{description}")
        trades = stage.get("trade_list") or []
        if trades:
            lines.append("- 交易清单：")
            for trade in trades:
                if isinstance(trade, dict):
                    lines.append(f"  - {compact_trade(trade)}")

    subjects = collect_subjects(data)
    if subjects:
        lines.append("")
        lines.append("## 主体候选清单")
        lines.append("")
        lines.append("| 主体 | 数据角色 | 出现位置/数值 |")
        lines.append("|---|---|---|")
        for name, role, note in subjects:
            lines.append(f"| {name} | {role} | {note} |")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并购重组画面数据文件，输出交易步骤核对表。")
    parser.add_argument("screen_data", type=Path, help="标的名称原始数据.txt/.rtf 的路径")
    parser.add_argument("--output", type=Path, help="可选：核对表输出路径")
    args = parser.parse_args()

    text = read_text(args.screen_data)
    payload = parse_payload(text)
    data = as_data(payload)
    markdown = render_markdown(args.screen_data, data)

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
