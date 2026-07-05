from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

RSS_URL = "https://news.google.com/rss/search"


def _cutoff(lookback_days):
    return datetime.now(timezone.utc) - timedelta(days=lookback_days)


def collect(config):
    search_terms = config["news_search_terms"]
    lookback_days = config["lookback_days"]
    news_cfg = config["news"]
    cutoff = _cutoff(lookback_days)

    seen_links = set()
    results = []
    for term in search_terms:
        query = quote(f'"{term}"')
        url = (
            f"{RSS_URL}?q={query}"
            f"&hl={news_cfg['language']}&gl={news_cfg['country']}&ceid={news_cfg['ceid']}"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.get("link")
            if not link or link in seen_links:
                continue
            published = entry.get("published_parsed")
            if not published:
                continue
            published_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if published_dt < cutoff:
                continue
            seen_links.add(link)
            results.append(
                {
                    "id": link,
                    "title": entry.get("title", ""),
                    "url": link,
                    "date": published_dt.strftime("%Y-%m-%d"),
                    "source": "news",
                    "snippet": "",
                }
            )

    return results
