#!/usr/bin/env python3
"""Fetch merger screen data and locate matching CNInfo announcements."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


TIMEOUT = 30
THS_BASE = "https://basic.10jqka.com.cn/basicapi/company_info/mergers_acquisition/v1"
CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_PDF_BASE = "https://static.cninfo.com.cn/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
DEFAULT_TITLE_KEYWORDS = (
    "重大资产重组",
    "筹划",
    "停牌",
    "发行股份",
    "购买资产",
    "吸收合并",
    "资产置换",
    "预案",
    "报告书",
)


class FetchError(RuntimeError):
    """Raised when a remote source cannot provide usable data."""


def request_bytes(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    form: dict[str, Any] | None = None,
    referer: str | None = None,
) -> tuple[bytes, str]:
    if params:
        url = f"{url}?{urlencode(params)}"
    body = urlencode(form).encode("utf-8") if form is not None else None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip",
    }
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    if referer:
        headers["Referer"] = referer

    request = Request(url, data=body, headers=headers)
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read()
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                payload = gzip.decompress(payload)
            return payload, response.geturl()
    except HTTPError as error:
        raise FetchError(f"HTTP {error.code}: {url}") from error
    except URLError as error:
        raise FetchError(f"网络请求失败：{error.reason}") from error
    except TimeoutError as error:
        raise FetchError(f"请求超时：{url}") from error


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    form: dict[str, Any] | None = None,
    referer: str | None = None,
) -> dict[str, Any]:
    payload, _ = request_bytes(url, params=params, form=form, referer=referer)
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FetchError(f"接口未返回有效 JSON：{url}") from error
    if not isinstance(result, dict):
        raise FetchError(f"接口 JSON 顶层不是对象：{url}")
    return result


def safe_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value).strip().strip(".")
    return cleaned or fallback


def normalize_date(value: Any) -> str:
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw[:10], pattern).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", raw)
    if match:
        return date(*(int(part) for part in match.groups())).isoformat()
    return raw


def fetch_screen_data(code: str, market: str, output_dir: Path) -> dict[str, Any]:
    common = {"show": "1", "code": code, "market": market, "type": "stock"}
    summary = request_json(f"{THS_BASE}/summary/", params=common)
    items = summary.get("data") or []
    if not isinstance(items, list) or not items:
        raise FetchError(f"未找到股票 {code}（market={market}）的并购重组案例")

    case = items[0]
    if not isinstance(case, dict) or not case.get("id"):
        raise FetchError("同花顺案例摘要缺少案例 ID")
    case_id = str(case["id"])
    first_date = normalize_date(case.get("date"))

    detail = request_json(
        f"{THS_BASE}/program_interpret/",
        params={"id": case_id, "code": code, "market": market, "type": "stock"},
    )
    data = detail.get("data")
    if not isinstance(data, dict):
        raise FetchError("同花顺案例详情缺少有效的 data 对象")

    company = data.get("company_info") or {}
    company_name = str(company.get("name") or case.get("name") or code).strip()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_filename(company_name, code)}原始数据.txt"
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    animation_url = (
        "https://basic.10jqka.com.cn/datav/mergesAcquistionsDynamic_v2.html"
        f"?id={case_id}&code={code}&marketid={market}"
    )
    return {
        "company": company_name,
        "code": code,
        "market": market,
        "case_id": case_id,
        "first_announcement_date": first_date,
        "animation_url": animation_url,
        "screen_data_path": str(output_path.resolve()),
    }


def infer_ths_market(code: str) -> str:
    """Infer the market values documented by the original ma-query skill."""
    return "15" if code.startswith("6") else "17"


def exchange_params(code: str) -> tuple[str, str]:
    if code.startswith(("5", "6", "9")):
        return "sse", "sh"
    if code.startswith(("4", "8")) or code.startswith("92"):
        return "bse", "bj"
    return "szse", "sz"


def clean_title(value: Any) -> str:
    title = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", title).strip()


def announcement_date(value: Any) -> str:
    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return normalize_date(value)
    china_time = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(milliseconds / 1000, tz=china_time).date().isoformat()


def cninfo_pdf_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    if raw.startswith("//"):
        return f"https:{raw}"
    return urljoin(CNINFO_PDF_BASE, raw.lstrip("/"))


def query_cninfo_page(
    code: str,
    company: str,
    start_date: date,
    end_date: date,
    page_number: int,
) -> dict[str, Any]:
    column, plate = exchange_params(code)
    form = {
        "pageNum": str(page_number),
        "pageSize": "30",
        "column": column,
        "tabName": "fulltext",
        "plate": plate,
        "stock": "",
        "searchkey": company,
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    return request_json(
        CNINFO_QUERY_URL,
        form=form,
        referer="http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    )


def score_announcement(
    item: dict[str, Any], first_date: date, keywords: tuple[str, ...], company: str
) -> tuple[int, list[str]]:
    title = clean_title(item.get("announcementTitle"))
    item_date_raw = announcement_date(item.get("announcementTime"))
    reasons: list[str] = []
    score = 0
    try:
        item_date = date.fromisoformat(item_date_raw)
        distance = abs((item_date - first_date).days)
        score += max(0, 30 - distance * 2)
        if distance == 0:
            score += 100
            reasons.append("与首次公告日期同日")
        else:
            reasons.append(f"距首次公告日期 {distance} 天")
    except ValueError:
        pass

    matched = [keyword for keyword in keywords if keyword and keyword in title]
    score += len(matched) * 18
    if matched:
        reasons.append("标题命中：" + "、".join(matched))
    if company and title.startswith(company):
        score += 12
        reasons.append("公司正式文件标题")
    if "进展" in title or "提示性" in title:
        score -= 5
    for term, penalty in (
        ("独立财务顾问", 45),
        ("核查意见", 35),
        ("法律意见", 35),
        ("董事会关于", 25),
        ("摘要", 10),
    ):
        if term in title:
            score -= penalty
    return score, reasons


def find_announcements(
    code: str,
    company: str,
    first_date: date,
    keywords: tuple[str, ...],
    days_before: int,
    days_after: int,
    limit: int,
) -> list[dict[str, Any]]:
    start_date = first_date - timedelta(days=days_before)
    end_date = first_date + timedelta(days=days_after)
    raw_items: list[dict[str, Any]] = []
    for page_number in range(1, 4):
        payload = query_cninfo_page(code, company, start_date, end_date, page_number)
        announcements = payload.get("announcements") or []
        if not isinstance(announcements, list):
            break
        raw_items.extend(item for item in announcements if isinstance(item, dict))
        if len(announcements) < 30 or not payload.get("hasMore"):
            break

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        if str(item.get("secCode") or "").strip() != code:
            continue
        pdf_url = cninfo_pdf_url(item.get("adjunctUrl"))
        dedupe_key = pdf_url or str(item.get("announcementId") or "")
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        score, reasons = score_announcement(item, first_date, keywords, company)
        candidates.append(
            {
                "date": announcement_date(item.get("announcementTime")),
                "title": clean_title(item.get("announcementTitle")),
                "pdf_url": pdf_url,
                "score": score,
                "match_reason": "；".join(reasons) or "日期窗口内同股票代码公告",
            }
        )

    candidates.sort(key=lambda item: (-int(item["score"]), str(item["date"]), str(item["title"])))
    return candidates[:limit]


def download_announcement(url: str, title: str, output_dir: Path, overwrite: bool) -> Path:
    resolved_url = cninfo_pdf_url(url)
    if not resolved_url:
        raise FetchError("公告 PDF URL 为空")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_filename(title, '公告')}.pdf"
    if output_path.exists() and not overwrite:
        if output_path.read_bytes()[:4] == b"%PDF":
            return output_path.resolve()
        raise FetchError(f"文件已存在且不是有效 PDF：{output_path}；可使用 --overwrite 覆盖")

    payload, final_url = request_bytes(resolved_url, referer="http://www.cninfo.com.cn/")
    if not payload.startswith(b"%PDF"):
        raise FetchError(f"下载结果不是 PDF：{final_url}")
    output_path.write_bytes(payload)
    return output_path.resolve()


def verify_candidates(codes: list[str]) -> list[dict[str, Any]]:
    """Verify that each candidate has retrievable merger screen data."""
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ma-candidate-check-") as temp_dir:
        output_dir = Path(temp_dir)
        for raw_code in codes:
            code = raw_code.strip()
            if not code:
                continue
            market = infer_ths_market(code)
            try:
                result = fetch_screen_data(code, market, output_dir)
                results.append(
                    {
                        "code": code,
                        "available": True,
                        "company": result["company"],
                        "case_id": result["case_id"],
                        "first_announcement_date": result["first_announcement_date"],
                    }
                )
            except (FetchError, OSError) as error:
                results.append(
                    {
                        "code": code,
                        "available": False,
                        "error": str(error),
                    }
                )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="获取并购重组画面原始数据，并按首次公告日期查找巨潮资讯公告候选。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch-data", help="获取并保存原始画面数据")
    fetch_parser.add_argument("code", help="股票代码，例如 300277")
    fetch_parser.add_argument(
        "--market",
        help="同花顺市场代码；不传时沪市 6 开头代码用 15，其余用 17",
    )
    fetch_parser.add_argument("--output-dir", type=Path, default=Path.cwd(), help="输出目录")
    fetch_parser.add_argument("--json", action="store_true", help="以 JSON 输出结果摘要")

    verify_parser = subparsers.add_parser(
        "verify-candidates",
        help="批量验证候选股票能否获取并购重组画面数据，不保留临时文件",
    )
    verify_parser.add_argument("codes", nargs="+", help="待验证的股票代码")
    verify_parser.add_argument("--json", action="store_true", help="以 JSON 输出验证结果")

    find_parser = subparsers.add_parser("find-announcements", help="查找公告候选，不下载")
    find_parser.add_argument("--code", required=True, help="股票代码")
    find_parser.add_argument("--company", required=True, help="首次公告时的公司简称")
    find_parser.add_argument("--first-date", required=True, help="首次公告日期 YYYY-MM-DD")
    find_parser.add_argument("--keywords", nargs="+", help="可选：标题优先匹配关键词")
    find_parser.add_argument("--days-before", type=int, default=1, help="向前搜索天数，默认 1")
    find_parser.add_argument("--days-after", type=int, default=14, help="向后搜索天数，默认 14")
    find_parser.add_argument("--limit", type=int, default=10, help="最多输出候选数，默认 10")
    find_parser.add_argument("--json", action="store_true", help="以 JSON 输出候选")

    download_parser = subparsers.add_parser(
        "download-announcement", help="下载用户已确认标题的公告 PDF"
    )
    download_parser.add_argument("--url", required=True, help="候选公告 PDF URL 或相对路径")
    download_parser.add_argument("--title", required=True, help="用户已确认的公告标题")
    download_parser.add_argument("--output-dir", type=Path, default=Path.cwd(), help="输出目录")
    download_parser.add_argument("--overwrite", action="store_true", help="覆盖同名文件")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "fetch-data":
            code = args.code.strip()
            market = str(args.market or infer_ths_market(code))
            result = fetch_screen_data(code, market, args.output_dir)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"公司：{result['company']}（{result['code']}）")
                print(f"案例 ID：{result['case_id']}")
                print(f"首次公告日期：{result['first_announcement_date']}")
                print(f"动画页面：{result['animation_url']}")
                print(f"原始数据：{result['screen_data_path']}")
            return 0

        if args.command == "verify-candidates":
            results = verify_candidates(args.codes)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for result in results:
                    if result["available"]:
                        print(
                            f"[可获取] {result['company']}（{result['code']}）"
                            f" | 案例 ID：{result['case_id']}"
                            f" | 首次公告日期：{result['first_announcement_date']}"
                        )
                    else:
                        print(f"[不可获取] {result['code']} | {result['error']}")
            return 0 if all(item["available"] for item in results) else 1

        if args.command == "find-announcements":
            first_date = date.fromisoformat(args.first_date)
            keywords = tuple(args.keywords or DEFAULT_TITLE_KEYWORDS)
            candidates = find_announcements(
                args.code.strip(),
                args.company.strip(),
                first_date,
                keywords,
                max(0, args.days_before),
                max(0, args.days_after),
                max(1, args.limit),
            )
            if args.json:
                print(json.dumps(candidates, ensure_ascii=False, indent=2))
            elif not candidates:
                print("未找到同股票代码的公告候选。请扩大日期窗口或核对公司简称。")
            else:
                print(f"公告候选（首次公告日期：{first_date.isoformat()}）")
                for index, candidate in enumerate(candidates, 1):
                    print(f"[{index}] {candidate['date']} | {candidate['title']}")
                    print(f"    PDF：{candidate['pdf_url']}")
                    print(f"    匹配：{candidate['match_reason']}")
                print("\n请把候选标题展示给用户并等待确认；确认前不要下载或进入内容创作。")
            return 0

        path = download_announcement(args.url, args.title, args.output_dir, args.overwrite)
        print(f"公告 PDF：{path}")
        return 0
    except ValueError as error:
        print(f"参数格式错误：{error}", file=sys.stderr)
    except FetchError as error:
        print(f"获取失败：{error}", file=sys.stderr)
    except OSError as error:
        print(f"文件操作失败：{error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
