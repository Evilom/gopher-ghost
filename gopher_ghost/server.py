"""A tiny Gopher server that haunts the modern web.

Usage: python -m gopher_ghost.server [--host 0.0.0.0] [--port 7070]
Port 70 is the canonical Gopher port (needs root); default here is 7070.
"""
import argparse
import os
import re
import socketserver
import urllib.parse

from . import feeds
from . import web as webmod
from .menu import end, info, item, text_body

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.environ.get(
    "GOPHER_GHOST_CONTENT",
    os.path.join(os.path.dirname(HERE), "content"),
)

# Haunted ASCII banner (type-i info lines). Keep lines under ~70 chars.
BANNER = r"""
      .-.
     (o o)     G O P H E R   G H O S T
      |O|         resurrected 1991
     '~~~'      for Kiroween 2026
  .-------------------------------.
  |  boo... the modern web walks  |
  |  again, as menus and text.    |
  '-------------------------------'
"""


class Router:
    def __init__(self, host, port, fetch=None):
        self.host, self.port = host, port
        self.fetch = fetch  # injectable for tests

    def link(self, itype, display, selector):
        return item(itype, display, selector, self.host, self.port)

    def handle(self, selector):
        selector = selector.strip()
        if selector in ("", "/"):
            return self.root()
        if selector == "/about":
            return self.text_file("about.txt")
        if selector == "/hn":
            return self.hn()
        m = re.fullmatch(r"/hn/(\d+)", selector)
        if m:
            return self.hn_thread(int(m.group(1)))
        if selector.startswith("/rss"):
            return self.rss(selector)
        if selector.startswith("/web"):
            return self.web_page(selector)
        if selector.startswith("/page/"):
            # /page/<urlencoded url>
            enc = selector[len("/page/"):]
            return self.web_page("/web?" + urllib.parse.unquote(enc))
        if selector.startswith("/text/"):
            name = selector[len("/text/"):]
            if re.fullmatch(r"[A-Za-z0-9_\-]+\.txt", name):
                return self.text_file(name)
        if selector.startswith("URL:"):
            return self.url_redirect(selector[4:])
        return self.error(f"Not found: {selector}")

    def root(self):
        out = [info(line) for line in BANNER.strip("\n").splitlines()]
        out += [
            info(""),
            info("* The ghost guide whispers: follow a number, fear nothing."),
            info("* Menus are type 1. Text is type 0. Search is type 7."),
            info(""),
            self.link("0", "About Gopher Ghost", "/about"),
            self.link("1", "Hacker News - top stories (live)", "/hn"),
            self.link("7", "Read any RSS/Atom feed (enter URL)", "/rss"),
            self.link(
                "1",
                "Example feed: Hacker News RSS",
                "/rss?https://hnrss.org/frontpage",
            ),
            self.link(
                "7",
                "Web page -> Gopher text (enter https URL)",
                "/web",
            ),
            self.link(
                "0",
                "Example page: example.com (as text)",
                "/web?https://example.com/",
            ),
            self.link("0", "A short history of Gopher", "/text/history.txt"),
            info(""),
            info("Built for Kiroween 2026 - category: Resurrection"),
            info("Official build path: keep refining this in Kiro."),
            end(),
        ]
        return "".join(out)

    def text_file(self, name):
        path = os.path.join(CONTENT_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                return text_body(f.read())
        except OSError:
            return self.error(f"No such text: {name}")

    def hn(self):
        kwargs = {"fetch": self.fetch} if self.fetch else {}
        try:
            stories = feeds.hn_top(limit=15, **kwargs)
        except Exception as e:  # network down, etc.
            return self.error(f"Could not reach Hacker News: {e}")
        out = [
            info("Hacker News - top stories"),
            info("Pick a story URL, or open Comments for the thread."),
            info(""),
        ]
        for i, s in enumerate(stories, 1):
            out.append(self.link("h", f"{i:2}. {s['title']}", "URL:" + s["url"]))
            out.append(
                info(
                    f"    {s['score']} points by {s['by']} | {s['comments']} comments"
                )
            )
            if s.get("id"):
                out.append(
                    self.link(
                        "1",
                        f"    >> Comments ({s['comments']})",
                        f"/hn/{s['id']}",
                    )
                )
        out.append(end())
        return "".join(out)

    def hn_thread(self, item_id, depth=0, max_kids=20):
        kwargs = {"fetch": self.fetch} if self.fetch else {}
        try:
            it = feeds.hn_item(item_id, **kwargs)
        except Exception as e:
            return self.error(f"Could not load HN item {item_id}: {e}")
        if it.get("dead"):
            return self.error(f"HN item {item_id} is gone")

        out = []
        if it["type"] == "story" or it.get("title"):
            out.append(info(it["title"] or f"HN #{item_id}"))
            out.append(info(f"by {it['by']} | {it['score']} points | id {item_id}"))
            if it.get("url"):
                out.append(self.link("h", "Open original URL", "URL:" + it["url"]))
                # also offer web->text proxy when it's http(s)
                if it["url"].startswith(("http://", "https://")):
                    out.append(
                        self.link(
                            "0",
                            "Read page as Gopher text",
                            "/web?" + it["url"],
                        )
                    )
            out.append(info(""))
        else:
            out.append(info(f"Comment by {it['by']} (id {item_id})"))
            out.append(info(""))

        text = it.get("text") or ""
        if text:
            # HN text is HTML; flatten lightly
            plain = webmod.html_to_text(text)
            for line in plain.splitlines() or [plain]:
                # wrap-ish: keep as info lines
                while len(line) > 70:
                    out.append(info(line[:70]))
                    line = line[70:]
                out.append(info(line))
            out.append(info(""))

        kids = (it.get("kids") or [])[:max_kids]
        if kids:
            out.append(info(f"-- {len(kids)} replies (nested menus) --"))
            for kid in kids:
                out.append(self.link("1", f"reply #{kid}", f"/hn/{kid}"))
        else:
            out.append(info("(no replies loaded)"))
        out.append(self.link("1", "Back to HN top", "/hn"))
        out.append(end())
        return "".join(out)

    def rss(self, selector):
        # Type-7 search sends "selector\tquery"; we also accept "/rss?url".
        url = ""
        if "\t" in selector:
            url = selector.split("\t", 1)[1].strip()
        elif "?" in selector:
            url = urllib.parse.unquote(selector.split("?", 1)[1])
        if not url:
            return self.error("Give me a feed URL")
        if not url.startswith(("http://", "https://")):
            return self.error("Only http(s) feeds are supported")
        kwargs = {"fetch": self.fetch} if self.fetch else {}
        try:
            entries = feeds.rss(url, **kwargs)
        except Exception as e:
            return self.error(f"Could not read feed: {e}")
        out = [info(f"Feed: {url}"), info("")]
        for e in entries:
            out.append(
                self.link("h", e["title"] or "(untitled)", "URL:" + e["link"])
            )
            if e.get("link", "").startswith(("http://", "https://")):
                out.append(
                    self.link(
                        "0",
                        "    read as text",
                        "/web?" + e["link"],
                    )
                )
        out.append(end())
        return "".join(out)

    def web_page(self, selector):
        url = ""
        if "\t" in selector:
            url = selector.split("\t", 1)[1].strip()
        elif "?" in selector:
            url = urllib.parse.unquote(selector.split("?", 1)[1])
        if not url:
            return self.error("Give me an https URL (type-7 search or /web?<url>)")
        kwargs = {}
        if self.fetch:
            kwargs["fetch"] = self.fetch
        try:
            text = webmod.fetch_page(url, **kwargs)
        except Exception as e:
            return self.error(f"Could not fetch page: {e}")
        return text_body(text)

    def url_redirect(self, url):
        # Common Gopher convention for linking to the web (type h, "URL:" selector).
        safe = url.replace("<", "").replace(">", "").replace('"', "")
        return (
            f'<html><head><meta http-equiv="refresh" content="0;url={safe}"></head>'
            f'<body>Leaving Gopherspace: <a href="{safe}">{safe}</a></body></html>'
        )

    def error(self, msg):
        return item("3", msg, "", "error.host", 1) + end()


def make_handler(router):
    class Handler(socketserver.StreamRequestHandler):
        timeout = 30

        def handle(self):
            raw = self.rfile.readline(4096).decode("utf-8", "replace")
            selector = raw.rstrip("\r\n")
            body = router.handle(selector)
            self.wfile.write(body.encode("utf-8"))

    return Handler


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host="0.0.0.0", port=7070, public_host=None):
    router = Router(
        public_host or ("localhost" if host in ("0.0.0.0", "") else host), port
    )
    with Server((host, port), make_handler(router)) as srv:
        print(f"Gopher Ghost haunting gopher://{router.host}:{port}/")
        srv.serve_forever()


def main():
    p = argparse.ArgumentParser(description="Gopher Ghost server")
    p.add_argument("--host", default=os.environ.get("GOPHER_HOST", "0.0.0.0"))
    p.add_argument(
        "--port", type=int, default=int(os.environ.get("GOPHER_PORT", "7070"))
    )
    p.add_argument("--public-host", default=os.environ.get("GOPHER_PUBLIC_HOST"))
    a = p.parse_args()
    serve(a.host, a.port, a.public_host)


if __name__ == "__main__":
    main()
