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
from .menu import end, info, item, text_body

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.environ.get("GOPHER_GHOST_CONTENT",
                             os.path.join(os.path.dirname(HERE), "content"))

BANNER = r"""
  .-------------------------------------------.
  |   G O P H E R   G H O S T     (boo, 1991) |
  |   the modern web, resurrected as Gopher   |
  '-------------------------------------------'
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
        if selector.startswith("/rss"):
            return self.rss(selector)
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
            self.link("0", "About Gopher Ghost", "/about"),
            self.link("1", "Hacker News - top stories (live)", "/hn"),
            self.link("7", "Read any RSS/Atom feed (enter URL)", "/rss"),
            self.link("1", "Example feed: Hacker News RSS", "/rss?https://hnrss.org/frontpage"),
            self.link("0", "A short history of Gopher", "/text/history.txt"),
            info(""),
            info("Built for Kiroween 2026 - category: Resurrection"),
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
        out = [info("Hacker News - top stories"), info("")]
        for i, s in enumerate(stories, 1):
            out.append(self.link("h", f"{i:2}. {s['title']}", "URL:" + s["url"]))
            out.append(info(f"    {s['score']} points by {s['by']} | {s['comments']} comments"))
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
            out.append(self.link("h", e["title"] or "(untitled)", "URL:" + e["link"]))
        out.append(end())
        return "".join(out)

    def url_redirect(self, url):
        # Common Gopher convention for linking to the web (type h, "URL:" selector).
        safe = url.replace("<", "").replace(">", "").replace('"', "")
        return (f'<html><head><meta http-equiv="refresh" content="0;url={safe}"></head>'
                f'<body>Leaving Gopherspace: <a href="{safe}">{safe}</a></body></html>')

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
    router = Router(public_host or ("localhost" if host in ("0.0.0.0", "") else host), port)
    with Server((host, port), make_handler(router)) as srv:
        print(f"Gopher Ghost haunting gopher://{router.host}:{port}/")
        srv.serve_forever()


def main():
    p = argparse.ArgumentParser(description="Gopher Ghost server")
    p.add_argument("--host", default=os.environ.get("GOPHER_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("GOPHER_PORT", "7070")))
    p.add_argument("--public-host", default=os.environ.get("GOPHER_PUBLIC_HOST"))
    a = p.parse_args()
    serve(a.host, a.port, a.public_host)


if __name__ == "__main__":
    main()
