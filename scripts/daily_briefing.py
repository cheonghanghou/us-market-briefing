import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.emailer import send_email
from lib.finnhub_client import get_earnings_today, get_general_news
from lib.textmatch import any_keyword, matching_keywords
from lib.yahoo import get_quote

NY = ZoneInfo("America/New_York")

MACRO_KEYWORDS = [
    "fed", "federal reserve", "rate", "inflation", "cpi", "ppi", "jobs", "payroll",
    "unemployment", "gdp", "treasury", "tariff", "trade war", "congress", "budget",
    "debt ceiling", "powell", "interest rate",
]
SECTOR_KEYWORDS = [
    "ai", "artificial intelligence", "chip", "semiconductor", "nvidia", "ev",
    "electric vehicle", "biotech", "pharma", "renewable", "solar", "cloud",
    "quantum", "robot",
]
COMPANY_NAMES = [
    "apple", "microsoft", "nvidia", "tesla", "amazon", "google", "alphabet", "meta",
    "netflix", "berkshire", "jpmorgan", "exxon", "amd", "intel", "boeing",
    "walmart", "disney", "oracle", "broadcom", "qualcomm",
]


def bucket(headlines):
    macro, sector, company = [], [], []
    for item in headlines:
        text = item.get("headline", "") + " " + item.get("summary", "")
        if any_keyword(text, MACRO_KEYWORDS):
            macro.append(item)
        elif any_keyword(text, SECTOR_KEYWORDS):
            sector.append(item)
        elif any_keyword(text, COMPANY_NAMES):
            company.append(item)
    return macro, sector, company


def fmt_pct(pct):
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def fmt_item(item, idx):
    headline = item.get("headline", "").strip()
    source = item.get("source", "")
    url = item.get("url", "").strip()
    line = f"{idx}. {headline}（来源：{source}）"
    if url:
        line += f"\n   链接：{url}"
    return line


def main():
    now = datetime.now(NY)
    date_str = now.strftime("%Y-%m-%d")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "reports", "daily", f"{date_str}.md")

    force = os.environ.get("FORCE_RUN") == "true"
    if not force and not (6 <= now.hour <= 13):
        print(f"当前纽约时间 {now.strftime('%Y-%m-%d %H:%M')}，不在触发窗口（6:00-13:59）内，退出。")
        return
    if os.path.exists(report_path):
        print(f"{date_str} 的简报已存在，跳过重复发送。")
        return

    finnhub_token = os.environ["FINNHUB_API_KEY"]
    gmail_addr = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]

    sp500 = get_quote("^GSPC")
    nasdaq = get_quote("^IXIC")
    dow = get_quote("^DJI")
    kweb = get_quote("KWEB")
    gold = get_quote("GC=F")
    oil = get_quote("CL=F")
    usdcny = get_quote("CNY=X")
    dxy = get_quote("DX-Y.NYB")

    news = get_general_news(finnhub_token, limit=80)
    macro, sector, company = bucket(news)
    earnings = get_earnings_today(finnhub_token, date_str)

    lines = [f"【盘前金融资讯简报｜{date_str}】", ""]

    lines.append("一、宏观要闻")
    if macro:
        for i, item in enumerate(macro[:3], 1):
            lines.append(fmt_item(item, i))
    else:
        lines.append("1. 今日未抓取到明显的宏观类新闻，建议自行关注美联储及经济数据动向。")
    lines.append("")

    lines.append("二、隔夜市场")
    lines.append(
        f"1. 美股：标普500 {sp500['price']:.2f}点（{fmt_pct(sp500['pct'])}）；"
        f"纳指 {nasdaq['price']:.2f}点（{fmt_pct(nasdaq['pct'])}）；"
        f"道指 {dow['price']:.2f}点（{fmt_pct(dow['pct'])}）"
    )
    lines.append(f"2. 中概股：中概股代理ETF KWEB {kweb['price']:.2f}（{fmt_pct(kweb['pct'])}）")
    lines.append(
        f"3. 商品：黄金期货 {gold['price']:.2f}美元/盎司（{fmt_pct(gold['pct'])}）；"
        f"WTI原油 {oil['price']:.2f}美元/桶（{fmt_pct(oil['pct'])}）"
    )
    lines.append(
        f"4. 汇率：美元指数 {dxy['price']:.2f}（{fmt_pct(dxy['pct'])}）；"
        f"美元兑人民币 {usdcny['price']:.4f}（{fmt_pct(usdcny['pct'])}）"
    )
    lines.append("")

    lines.append("三、行业热点")
    if sector:
        for i, item in enumerate(sector[:3], 1):
            lines.append(fmt_item(item, i))
    else:
        lines.append("1. 今日未抓取到明显的行业热点新闻。")
    lines.append("")

    lines.append("四、重点公司")
    if company:
        for i, item in enumerate(company[:3], 1):
            lines.append(fmt_item(item, i))
    else:
        lines.append("1. 今日未抓取到重点公司相关新闻。")
    lines.append("")

    lines.append("五、今日关注")
    if earnings:
        tickers = ", ".join(sorted({e["symbol"] for e in earnings if e.get("symbol")})[:15])
        lines.append(f"1. 今日财报发布公司（部分）：{tickers}")
    else:
        lines.append("1. 今日暂无重要财报发布安排（或数据源未覆盖）。")
    lines.append("2. 经济数据日历当前数据源（Finnhub免费版）未开放，建议自行查看 https://www.investing.com/economic-calendar/")
    lines.append("")

    lines.append("六、操作提示")
    if sp500["pct"] > 1:
        mood = "情绪偏乐观"
    elif sp500["pct"] < -1:
        mood = "情绪偏谨慎"
    else:
        mood = "情绪中性"
    lines.append(f"- 今日情绪关注：标普500最近一个交易日{fmt_pct(sp500['pct'])}，{mood}")

    matched_kw = set()
    for item in sector:
        text = item.get("headline", "") + " " + item.get("summary", "")
        matched_kw.update(matching_keywords(text, SECTOR_KEYWORDS))
    watch_sectors = "、".join(sorted(matched_kw)) if matched_kw else "暂无明显行业信号"
    lines.append(f"- 重点观察板块：{watch_sectors}")
    lines.append("- 以上内容为脚本自动抓取整理，不构成投资建议。")

    body = "\n".join(lines)

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(body)

    send_email(f"【盘前金融资讯简报｜{date_str}】", body, gmail_addr, gmail_pass)
    print(f"简报已生成并发送：{report_path}")


if __name__ == "__main__":
    main()
