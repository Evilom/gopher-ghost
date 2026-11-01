"""Fetch modern content (Hacker News, RSS/Atom) and flatten it for Gopher."""
import json
import textwrap
import time
import urllib.request
import xml.etree.ElementTree as ET

UA = "gopher-ghost/0.1 (+https://github.com/Evilom/gopher-ghost)"
HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

_cache = {}
CACHE_SECONDS = 300


def _get(url, timeout=10):
    now = time.time()
    hit = _cache.get(url)
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    _cache[url] = (now, data)
    return data


def hn_top(limit=15, fetch=_get):
    ids = json.loads(fetch(HN_TOP))[:limit]
    stories = []
    for sid in ids:
        try:
            it = json.loads(fetch(HN_ITEM.format(sid)))
        except Exception:
            continue
        if not it:
            continue
        stories.append({
            "id": it.get("id"),
            "title": it.get("title", "(untitled)"),
            "url": it.get("url", f"https://news.ycombinator.com/item?id={sid}"),
            "score": it.get("score", 0),
            "by": it.get("by", "?"),
            "comments": it.get("descendants", 0),
        })
    return stories


def _strip(tag):
    return tag.split("}", 1)[-1]


def parse_feed(xml_bytes, limit=20):
    """Parse RSS 2.0 or Atom into [{'title','link','summary'}]."""
    root = ET.fromstring(xml_bytes)
    out = []
    for el in root.iter():
        name = _strip(el.tag)
        if name not in ("item", "entry"):
            continue
        entry = {"title": "", "link": "", "summary": ""}
        for child in el:
            cname = _strip(child.tag)
            if cname == "title":
                entry["title"] = (child.text or "").strip()
            elif cname == "link":
                entry["link"] = (child.get("href") or child.text or "").strip()
            elif cname in ("description", "summary", "content") and not entry["summary"]:
                entry["summary"] = (child.text or "").strip()
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def rss(url, limit=20, fetch=_get):
    return parse_feed(fetch(url), limit)


def wrap(text, width=70):
    return "\n".join(textwrap.fill(p, width) for p in text.split("\n"))
