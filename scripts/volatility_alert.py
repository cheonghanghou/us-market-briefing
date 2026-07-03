import json
import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.emailer import send_email
from lib.finnhub_client import get_general_news
from lib.textmatch import any_keyword
from lib.yahoo import get_quote

NY = ZoneInfo("America/New_York")

MAJOR_NEWS_KEYWORDS = [
    "emergency", "crash", "plunge", "surges", "war", "invade", "invasion",
    "attack", "resign", "resignation", "bankruptcy", "default", "collapse",
    "sanctions", "ceasefire", "coup",
]


def in_trading_hours(now):
    if now.weekday() >= 5:
        return False
    return time(9, 0) <= now.time() <= time(16, 30)


def magnitude_tier(pct_list, vix_pct):
    max_abs = max(abs(p) for p in pct_list)
    if max_abs >= 2.5 or vix_pct >= 30:
        return 2
    if max_abs >= 1.5 or vix_pct >= 15:
        return 1
    return 0


def find_major_news(news_items):
    hits = []
    for item in news_items:
        text = item.get("headline", "") + " " + item.get("summary", "")
        if any_keyword(text, MAJOR_NEWS_KEYWORDS):
            hits.append(item.get("headline", "").strip())
    return hits


def main():
    now = datetime.now(NY)
    force = os.environ.get("FORCE_RUN") == "true"
    if not force and not in_trading_hours(now):
        print(f"当前纽约时间 {now.strftime('%Y-%m-%d %H:%M')}，不在交易时段内，退出。")
        return

    date_str = now.strftime("%Y-%m-%d")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_path = os.path.join(base_dir, "state", f"alert_state_{date_str}.json")

    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"magnitude_tier": 0, "news_alerts": []}

    finnhub_token = os.environ["FINNHUB_API_KEY"]
    gmail_addr = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]

    sp500 = get_quote("^GSPC")
    nasdaq = get_quote("^IXIC")
    vix = get_quote("^VIX")

    tier = magnitude_tier([sp500["pct"], nasdaq["pct"]], vix["pct"])

    news = get_general_news(finnhub_token, limit=80)
    major_news = find_major_news(news)
    new_news = [n for n in major_news if n not in state["news_alerts"]]

    trigger_magnitude = tier > state["magnitude_tier"]
    trigger_news = len(new_news) > 0

    if not trigger_magnitude and not trigger_news:
        print(
            f"未触发提醒。当前标普500 {sp500['pct']:.2f}%，纳指 {nasdaq['pct']:.2f}%，"
            f"VIX {vix['pct']:.2f}%，档位 {tier}。"
        )
        return

    reasons = []
    if trigger_magnitude:
        reasons.append(f"波动幅度升级至档位{tier}")
    if trigger_news:
        reasons.append("发现重大突发新闻")

    lines = [
        f"当前纽约时间：{now.strftime('%Y-%m-%d %H:%M')} ET",
        f"标普500：{sp500['price']:.2f}点（{sp500['pct']:+.2f}%）",
        f"纳指：{nasdaq['price']:.2f}点（{nasdaq['pct']:+.2f}%）",
        f"VIX：{vix['price']:.2f}（{vix['pct']:+.2f}%）",
        f"触发原因：{'、'.join(reasons)}",
    ]
    if new_news:
        lines.append("相关重大新闻：")
        for n in new_news[:5]:
            lines.append(f"- {n}")
    lines.append("")
    lines.append("以上内容仅供参考，不构成投资建议。")
    body = "\n".join(lines)

    time_str = now.strftime("%H%M")
    alert_path = os.path.join(base_dir, "reports", "alerts", f"{date_str}_{time_str}.md")
    os.makedirs(os.path.dirname(alert_path), exist_ok=True)
    with open(alert_path, "w", encoding="utf-8") as f:
        f.write(body)

    subject = f"【盘中异动提醒｜{date_str} {now.strftime('%H:%M')} ET】"
    send_email(subject, body, gmail_addr, gmail_pass)

    state["magnitude_tier"] = max(state["magnitude_tier"], tier)
    state["news_alerts"] = state["news_alerts"] + new_news
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"提醒已发送：{alert_path}")


if __name__ == "__main__":
    main()
