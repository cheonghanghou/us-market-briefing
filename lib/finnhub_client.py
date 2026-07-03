from .http import get_json


def get_general_news(token, limit=80):
    url = f"https://finnhub.io/api/v1/news?category=general&token={token}"
    data = get_json(url)
    return data[:limit]


def get_earnings_today(token, date_str):
    url = f"https://finnhub.io/api/v1/calendar/earnings?from={date_str}&to={date_str}&token={token}"
    data = get_json(url)
    return data.get("earningsCalendar", [])
