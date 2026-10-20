"""Send GitHub Trending summaries to a Feishu custom bot."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


BASE_URL = "https://github.com/trending"
TIMEOUT_SECONDS = 20
TOP_COUNT = 10
DESCRIPTION_LIMIT = 100
MAX_FEISHU_PAYLOAD_BYTES = 18_000
BEIJING = ZoneInfo("Asia/Shanghai")


class TrendingParser(HTMLParser):
    """Read repository cards from the public GitHub Trending HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, str]] = []
        self.card: dict[str, object] | None = None
        self.description_active = False
        self.language_active = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article" and "Box-row" in (attributes.get("class") or "").split():
            self.card = {
                "text": [],
                "description_parts": [],
                "language_parts": [],
                "repo": "",
                "url": "",
                "description": "",
                "language": "",
            }
            return

        if self.card is None:
            return

        if tag == "a" and not self.card["repo"]:
            href = attributes.get("href") or ""
            if re.fullmatch(r"/[^/]+/[^/]+", href):
                self.card["repo"] = href.lstrip("/")
                self.card["url"] = f"https://github.com{href}"

        if tag == "p" and not self.card["description"]:
            self.description_active = True
        if tag == "span" and attributes.get("itemprop") == "programmingLanguage":
            self.language_active = True

    def handle_endtag(self, tag: str) -> None:
        if self.card is None:
            return

        if tag == "p" and self.description_active:
            self.card["description"] = " ".join(self.card["description_parts"]).strip()
            self.description_active = False
        elif tag == "span" and self.language_active:
            self.card["language"] = " ".join(self.card["language_parts"]).strip()
            self.language_active = False
        elif tag == "article":
            item = self._finish_card()
            if item:
                self.items.append(item)
            self.card = None

    def handle_data(self, data: str) -> None:
        if self.card is None:
            return
        self.card["text"].append(data)
        if self.description_active:
            self.card["description_parts"].append(data)
        if self.language_active:
            self.card["language_parts"].append(data)

    def _finish_card(self) -> dict[str, str] | None:
        assert self.card is not None
        repo = str(self.card["repo"])
        if not repo:
            return None

        full_text = " ".join(self.card["text"])
        match = re.search(
            r"([\d,]+)\s+stars?\s+(today|this week|this month)\b",
            full_text,
            flags=re.IGNORECASE,
        )
        stars = match.group(1) if match else "未显示"
        period = match.group(2).lower() if match else ""
        description = re.sub(r"\s+", " ", str(self.card["description"])).strip()
        language = re.sub(r"\s+", " ", str(self.card["language"])).strip()
        return {
            "repo": repo,
            "url": str(self.card["url"]),
            "description": description or "暂无项目简介",
            "language": language or "未标注语言",
            "stars": stars,
            "period": period,
        }


def fetch_trending(period: str) -> list[dict[str, str]]:
    query = urlencode({"since": period})
    request = Request(
        f"{BASE_URL}?{query}",
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "github-trending-feishu/1.0",
        },
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = TrendingParser()
    parser.feed(html)
    if not parser.items:
        raise ValueError("页面中没有找到热榜项目")
    return parser.items[:TOP_COUNT]


def escape_markdown(text: str) -> str:
    special_characters = "\\" + chr(96) + "*_{}[]()#+-.!|>"
    for character in special_characters:
        text = text.replace(character, "\\" + character)
    return text


def format_section(
    title: str,
    period_label: str,
    items: list[dict[str, str]],
    description_limit: int,
) -> str:
    lines = [f"**{title}**"]
    for index, item in enumerate(items, start=1):
        repo = escape_markdown(item["repo"])
        language = escape_markdown(item["language"])
        description = ""
        if description_limit:
            description = escape_markdown(item["description"][:description_limit])
            if len(item["description"]) > description_limit:
                description += "…"
            description = f"\n   {description}"
        lines.append(
            f"{index}. [{repo}]({item['url']}) · {language} · "
            f"⭐ +star{item['stars']} {period_label}{description}"
        )
    return "\n\n".join(lines)


def build_card(
    now: datetime,
    section_data: list[tuple[str, str, list[dict[str, str]]]],
    failures: list[str],
) -> tuple[dict[str, object], int]:
    for description_limit in (DESCRIPTION_LIMIT, 70, 40, 20, 0):
        sections = [
            format_section(title, period_label, items, description_limit)
            for title, period_label, items in section_data
        ]
        body_parts = [
            f"统计日期：{now:%Y-%m-%d}（北京时间）",
            "数据来源：GitHub Trending，每个榜单展示前 10 个项目。",
            *sections,
        ]
        if failures:
            body_parts.append(
                "⚠️ 以下榜单抓取失败：\n"
                + "\n".join(f"- {reason}" for reason in failures)
            )

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "blue",
                    "title": {
                        "tag": "plain_text",
                        "content": f"GitHub热榜 · {now:%Y-%m-%d}",
                    },
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n\n".join(body_parts),
                        },
                    }
                ],
            },
        }
        payload_size = len(json.dumps(card, ensure_ascii=False).encode("utf-8"))
        if payload_size <= MAX_FEISHU_PAYLOAD_BYTES:
            return card, description_limit
    raise ValueError("热榜消息超过飞书机器人允许的大小")


def send_to_feishu(webhook: str, card: dict[str, object]) -> None:
    request = Request(
        webhook,
        data=json.dumps(card, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "github-trending-feishu/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        raise RuntimeError(f"飞书返回 HTTP {error.code}") from None
    except URLError:
        raise RuntimeError("无法连接飞书机器人，请检查网络或 Webhook Secret") from None

    if not 200 <= status < 300:
        raise RuntimeError(f"飞书返回 HTTP {status}")

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        raise RuntimeError("飞书返回内容无法识别") from None

    if isinstance(result, dict):
        for field in ("StatusCode", "code"):
            code = result.get(field)
            if code is not None and str(code) != "0":
                raise RuntimeError(f"飞书机器人拒绝消息（状态码 {code}）")


def main() -> int:
    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        print("[FAIL] 缺少仓库 Secret：FEISHU_WEBHOOK")
        return 1
    if not webhook.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        print("[FAIL] FEISHU_WEBHOOK 不是飞书自定义机器人的 Webhook 地址")
        return 1

    now = datetime.now(BEIJING)
    requested = [("daily", "今日热榜", "today")]
    if now.weekday() == 0:
        requested.append(("weekly", "本周热榜", "this week"))
    if now.day == 1:
        requested.append(("monthly", "本月热榜", "this month"))

    section_data: list[tuple[str, str, list[dict[str, str]]]] = []
    failures: list[str] = []
    for period, title, period_label in requested:
        try:
            items = fetch_trending(period)
            section_data.append((title, period_label, items))
            print(f"[OK] 已获取{title}（{len(items)} 个项目）")
        except (HTTPError, URLError) as error:
            status = f"HTTP {error.code}" if isinstance(error, HTTPError) else "网络连接失败"
            failures.append(f"{title}：{status}")
            print(f"[WARN] {title}获取失败：{status}")
        except (TimeoutError, ValueError, OSError) as error:
            reason = "请求超时" if isinstance(error, TimeoutError) else "页面解析失败"
            failures.append(f"{title}：{reason}")
            print(f"[WARN] {title}获取失败：{reason}")

    try:
        card, description_limit = build_card(now, section_data, failures)
    except ValueError as error:
        print(f"[FAIL] {error}")
        return 1
    if description_limit < DESCRIPTION_LIMIT:
        print("[WARN] 项目简介已缩短，以符合飞书机器人消息大小限制")

    try:
        send_to_feishu(webhook, card)
    except RuntimeError as error:
        print(f"[FAIL] 飞书推送失败：{error}")
        return 1

    if failures:
        print("[WARN] 已将可用榜单和失败提示推送到飞书；本次工作流标记为失败以便查看日志")
        return 1
    print("[OK] 热榜已推送到飞书")
    return 0


if __name__ == "__main__":
    sys.exit(main())
