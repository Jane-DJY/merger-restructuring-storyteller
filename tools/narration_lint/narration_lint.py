#!/usr/bin/env python3
"""并购重组旁白稿轻量检查工具。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BANNED_PATTERNS = [
    "对应到画面里",
    "先把关系讲清楚",
    "先来讲清楚",
    "我们来拆一下",
    "画面数据里",
    "画面显示",
    "视频里",
    "对应画面",
    "公司解释",
    "资料显示",
    "这不是",
    "真正的",
    "真正改变",
    "真正要看",
    "最值得",
    "最核心",
    "最关键",
    "最重要",
    "跨进",
    "必涨",
    "闭眼买",
    "十倍",
    "王炸",
    "逆天",
]

LIMITED_PATTERNS = {
    "不是": 1,
    "而是": 1,
}

ODD_WORDING_HINTS = {
    "跨进": "可改为“进入”“收购一家……公司”“新增……业务”。",
    "杀入": "口播稿不宜用情绪化动词，可改为“进入”。",
    "豪赌": "避免夸张判断，可改为“布局”或直接写交易事实。",
}

ABSTRACT_MACRO_HINTS = [
    "数字经济",
    "人工智能",
    "算力基础设施",
    "新质生产力",
    "产业升级",
]


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def lint(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    style_text = re.split(r"\n#{1,3}\s*来源\b", text, maxsplit=1)[0]
    errors: list[str] = []
    warnings: list[str] = []

    pure_match = re.search(r"^#{1,2}\s*纯文案版\s*$", text, flags=re.M)
    is_pure_script = bool(pure_match)
    if not is_pure_script and not re.search(r"^#{1,2}\s*(?:分段脚本|主版旁白)", text, flags=re.M):
        errors.append("缺少必要栏目：分段脚本")
    if "视频大标题" not in text and not re.search(r"^#{1,2}\s*大标题", text, flags=re.M):
        errors.append("缺少必要栏目：视频大标题")
    if "分段脚本" in text:
        source_match = re.search(r"^#{1,3}\s*来源\s*$", text, flags=re.M)
        if not source_match:
            errors.append("缺少必要栏目：来源")
        if not pure_match:
            errors.append("缺少必要栏目：纯文案版")
        elif source_match and pure_match.start() < source_match.start():
            errors.append("纯文案版必须放在来源清单之后")
        else:
            pure_text = text[pure_match.end():]
            if not re.search(r"^#{1,3}\s*视频大标题\s*$", pure_text, flags=re.M):
                errors.append("纯文案版缺少视频大标题")

            main_start = re.search(r"^#{1,2}\s*(?:分段脚本|主版旁白).*?$", text, flags=re.M)
            if main_start and source_match:
                main_text = text[main_start.end():source_match.start()]
                main_titles = re.findall(r"^#{2,4}\s+(.+?)\s*$", main_text, flags=re.M)
                pure_titles = [
                    title
                    for title in re.findall(r"^#{2,4}\s+(.+?)\s*$", pure_text, flags=re.M)
                    if title != "视频大标题"
                ]
                missing_titles = [title for title in main_titles if title not in pure_titles]
                if missing_titles:
                    errors.append(
                        "纯文案版缺少主版段落小标题：" + "、".join(missing_titles)
                    )

        for field in ["【画面】", "【来源】", "【核实内容】"]:
            if field not in text:
                errors.append(f"缺少必要字段：{field}")
        allowed_screens = {"并购重组范式", "html chart", "白板", "b-roll素材"}
        for match in re.finditer(r"【画面】：([^\n]+)", text):
            screen = match.group(1).strip()
            if screen not in allowed_screens:
                warnings.append(
                    f"第 {line_number(text, match.start())} 行：画面类型 `{screen}` 不在四选一范围内。"
                )

        main_end = source_match.start() if source_match else len(text)
        main_delivery_text = text[:main_end]
        screen_matches = list(re.finditer(r"【画面】：([^\n]+)", main_delivery_text))
        for index, match in enumerate(screen_matches):
            screen = match.group(1).strip()
            segment_end = (
                screen_matches[index + 1].start()
                if index + 1 < len(screen_matches)
                else len(main_delivery_text)
            )
            after_screen = main_delivery_text[match.end():segment_end].lstrip()
            has_immediate_chart_data = after_screen.startswith("【画面数据】：")
            if screen == "html chart":
                if not has_immediate_chart_data:
                    errors.append(
                        f"第 {line_number(text, match.start())} 行：html chart 必须在【画面】后立即提供【画面数据】。"
                    )
                    continue
                data_block = after_screen.split("【来源】：", 1)[0]
                required_columns = ["主体", "指标", "期间", "数值", "单位"]
                missing_columns = [column for column in required_columns if column not in data_block]
                if missing_columns:
                    errors.append(
                        f"第 {line_number(text, match.start())} 行：【画面数据】缺少字段："
                        + "、".join(missing_columns)
                    )
            elif has_immediate_chart_data:
                warnings.append(
                    f"第 {line_number(text, match.start())} 行：只有 html chart 需要【画面数据】，当前画面为 `{screen}`。"
                )

        if pure_match:
            pure_text_for_fields = text[pure_match.end():]
            if "【画面数据】" in pure_text_for_fields:
                errors.append("纯文案版不得保留【画面数据】。")

    standalone_subtitle = re.search(r"^#{1,3}\s*视频大标题和小标题\s*$|^小标题[:：]", text, flags=re.M)
    if standalone_subtitle:
        warnings.append(
            "发现单独的小标题清单。默认应把画面步骤小标题嵌入主版旁白内部，而不是文末单列。"
        )

    optional_sections = ["快节奏版", "短版", "配音提示", "分镜脚本"]
    for section in optional_sections:
        if section in text:
            warnings.append(
                f"出现附加栏目 `{section}`。默认交付不得包含该栏目，请确认用户是否明确要求。"
            )

    for phrase in BANNED_PATTERNS:
        for match in re.finditer(re.escape(phrase), style_text):
            warnings.append(f"第 {line_number(text, match.start())} 行：出现不宜表达 `{phrase}`")

    absolute_patterns = [
        (r"最[^，。；;\n]{0,8}(?:看|关键|核心|重要|本质|主要)", "避免 `最...` 这类绝对化强调，可改成“要看的是”“需要关注的是”。"),
        (r"真正[^，。；;\n]{0,10}是", "避免 `真正的...是` 或 `真正...是`，可改成更克制的事实描述。"),
    ]
    for pattern, hint in absolute_patterns:
        for match in re.finditer(pattern, style_text):
            warnings.append(f"第 {line_number(text, match.start())} 行：表达 `{match.group(0)}` 语气偏绝对。{hint}")

    template_titles = ["开场：交易为什么发生", "收束：交易完成后", "结尾", "总结"]
    for title in template_titles:
        if re.search(rf"^#{{1,4}}\s*{re.escape(title)}\s*$", text, flags=re.M):
            warnings.append(f"出现模板化小标题 `{title}`，建议改成有叙事功能的小标题。")

    for phrase, limit in LIMITED_PATTERNS.items():
        matches = list(re.finditer(re.escape(phrase), style_text))
        if len(matches) > limit:
            lines = ", ".join(str(line_number(text, m.start())) for m in matches[:6])
            warnings.append(
                f"`{phrase}` 出现 {len(matches)} 次，超过最多 {limit} 次的限制；请在初稿和润色阶段清理虚假对立句式。位置：第 {lines} 行。"
            )

    for phrase, hint in ODD_WORDING_HINTS.items():
        for match in re.finditer(re.escape(phrase), style_text):
            warnings.append(f"第 {line_number(text, match.start())} 行：表达 `{phrase}` 可能生硬。{hint}")

    for phrase in ABSTRACT_MACRO_HINTS:
        for match in re.finditer(re.escape(phrase), style_text):
            warnings.append(
                f"第 {line_number(text, match.start())} 行：出现宏观行业词 `{phrase}`。请确认已解释到公司为什么需要交易、标的为什么合适，不要用大词代替原因。"
            )

    long_subject_lists = re.finditer(r"[^。\n；;，,]*、[^。\n；;，,]*、[^。\n；;，,]*(?:、[^。\n；;，,]*)*等\s*\d+\s*名", style_text)
    for match in long_subject_lists:
        warnings.append(
            f"第 {line_number(text, match.start())} 行：多名主体连续点名后再写“等 N 名”，口播可能啰嗦；正文建议只保留前两个主体。"
        )

    long_digit_runs = re.findall(r"\d+(?:\.\d+)?%|\d{6,}", text)
    if len(long_digit_runs) > 12:
        warnings.append(
            f"发现 {len(long_digit_runs)} 个数字项。请检查每个数字是否都有助于观众理解。"
        )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并购重组旁白稿是否包含必要栏目和不宜表达。")
    parser.add_argument("markdown", type=Path)
    args = parser.parse_args()

    errors, warnings = lint(args.markdown)
    if errors:
        print("错误：")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("提醒：")
        for item in warnings:
            print(f"- {item}")
    if not errors and not warnings:
        print("通过：旁白稿检查无明显问题。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
