import re


def _pattern(keyword):
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)


def any_keyword(text, keywords):
    return any(_pattern(kw).search(text) for kw in keywords)


def matching_keywords(text, keywords):
    return [kw for kw in keywords if _pattern(kw).search(text)]
