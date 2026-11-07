import json
import os
import sys
import threading
import unittest
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gopher_ghost import client, feeds, web  # noqa: E402
from gopher_ghost.http_gateway import (  # noqa: E402
    lookslike_menu,
    make_handler,
    render_menu_html,
    render_text_html,
)
from gopher_ghost.menu import item, parse_menu, text_body  # noqa: E402
from gopher_ghost.server import Router, Server, make_handler as make_gopher_handler  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from urllib.request import urlopen  # noqa: E402

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Hello ghost</title><link>https://example.com/a</link></item>
<item><title>Second</title><link>https://example.com/b</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom one</title><link href="https://example.com/x"/></entry></feed>"""

SAMPLE_HTML = b"""<!DOCTYPE html><html><head><title>Spooky Page</title>
<style>body{color:red}</style></head><body>
<script>alert(1)</script>
<h1>Haunted Header</h1>
<p>Hello <b>ghost</b> world.</p>
<a href="/x">link</a>
</body></html>"""


def fake_fetch(url):
    if url == feeds.HN_TOP:
        return b"[1, 2]"
    if url.endswith("/item/1.json") or "item/1.json" in url:
        return json.dumps({
            "id": 1, "title": "Story one", "url": "https://e.com/1",
            "score": 10, "by": "pg", "descendants": 3, "kids": [10],
            "type": "story",
        }).encode()
    if url.endswith("/item/2.json") or "item/2.json" in url:
        return json.dumps({
            "id": 2, "title": "Story two", "score": 5, "by": "dang",
            "type": "story", "kids": [],
        }).encode()
    if url.endswith("/item/10.json") or "item/10.json" in url:
        return json.dumps({
            "id": 10, "type": "comment", "by": "alice",
            "text": "Nice <i>post</i>!", "kids": [], "parent": 1,
        }).encode()
    if "example.com" in url and "feed" not in url:
        return SAMPLE_HTML
    return RSS


class MenuTests(unittest.TestCase):
    def test_item_format(self):
        self.assertEqual(item("1", "Hi", "/x", "h", 70), "1Hi\t/x\th\t70\r\n")

    def test_dot_stuffing(self):
        body = text_body(".hidden\nok")
        self.assertTrue(body.startswith("..hidden"))
        self.assertTrue(body.endswith("\r\n.\r\n"))

    def test_parse_menu_roundtrip(self):
        raw = item("0", "Doc", "/d", "h", 7070) + ".\r\n"
        self.assertEqual(parse_menu(raw)[0]["selector"], "/d")


class FeedTests(unittest.TestCase):
    def test_rss(self):
        e = feeds.parse_feed(RSS)
        self.assertEqual([x["title"] for x in e], ["Hello ghost", "Second"])

    def test_atom(self):
        e = feeds.parse_feed(ATOM)
        self.assertEqual(e[0]["link"], "https://example.com/x")

    def test_hn_item(self):
        it = feeds.hn_item(10, fetch=fake_fetch)
        self.assertEqual(it["by"], "alice")
        self.assertEqual(it["type"], "comment")


class WebTests(unittest.TestCase):
    def test_html_to_text_strips_tags(self):
        text = web.html_to_text(SAMPLE_HTML)
        self.assertIn("Spooky Page", text)
        self.assertIn("Haunted Header", text)
        self.assertIn("Hello ghost world", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("alert", text)

    def test_sanitize_blocks_file(self):
        with self.assertRaises(ValueError):
            web.sanitize_url("file:///etc/passwd")

    def test_sanitize_blocks_javascript(self):
        with self.assertRaises(ValueError):
            web.sanitize_url("javascript:alert(1)")

    def test_sanitize_adds_https(self):
        self.assertTrue(web.sanitize_url("example.com").startswith("https://"))

    def test_fetch_page(self):
        text = web.fetch_page("https://example.com/", fetch=fake_fetch)
        self.assertIn("Source: https://example.com/", text)
        self.assertIn("Haunted Header", text)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.r = Router("localhost", 7070, fetch=fake_fetch)

    def test_root_haunted(self):
        raw = self.r.handle("")
        self.assertIn("G O P H E R   G H O S T", raw)
        entries = parse_menu(raw)
        sels = [e["selector"] for e in entries]
        self.assertIn("/hn", sels)
        self.assertIn("/about", sels)
        self.assertIn("/web", sels)

    def test_hn(self):
        entries = parse_menu(self.r.handle("/hn"))
        links = [e for e in entries if e["type"] == "h"]
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["selector"], "URL:https://e.com/1")
        comment_dirs = [e for e in entries if e["selector"] == "/hn/1"]
        self.assertTrue(comment_dirs)

    def test_hn_thread(self):
        entries = parse_menu(self.r.handle("/hn/1"))
        self.assertTrue(any(e["display"].startswith("Story one") or e["type"] == "i"
                            for e in entries))
        self.assertTrue(any(e["selector"] == "/hn/10" for e in entries))

    def test_rss_query(self):
        entries = parse_menu(self.r.handle("/rss\thttps://example.com/feed"))
        titles = [e["display"] for e in entries if e["type"] == "h"]
        self.assertIn("Second", titles)

    def test_web_query(self):
        body = self.r.handle("/web?https://example.com/")
        self.assertIn("Haunted Header", body)
        self.assertTrue(body.endswith(".\r\n") or body.rstrip().endswith("."))

    def test_web_tab_query(self):
        body = self.r.handle("/web\thttps://example.com/")
        self.assertIn("Spooky Page", body)

    def test_web_bad_scheme(self):
        body = self.r.handle("/web?file:///etc/passwd")
        self.assertTrue(body.startswith("3"))

    def test_text(self):
        self.assertIn("Gopher", self.r.handle("/about"))

    def test_path_traversal_rejected(self):
        self.assertTrue(self.r.handle("/text/../../etc/passwd").startswith("3"))

    def test_not_found(self):
        self.assertTrue(self.r.handle("/nope").startswith("3"))


class LiveSocketTest(unittest.TestCase):
    def test_tcp_roundtrip(self):
        router = Router("127.0.0.1", 0, fetch=fake_fetch)
        srv = Server(("127.0.0.1", 0), make_gopher_handler(router))
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            raw = client.fetch("127.0.0.1", port, "")
            self.assertIn("Hacker News", raw)
            self.assertIn("G O P H E R", raw)
            about = client.fetch("127.0.0.1", port, "/about")
            self.assertIn("Gopher Ghost", about)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_parse_url(self):
        self.assertEqual(
            client.parse_url("gopher://h:7070/0/about"),
            ("h", 7070, "0", "/about"),
        )


class HttpGatewayTests(unittest.TestCase):
    def test_lookslike_menu(self):
        menu = item("1", "Hi", "/x", "h", 70) + ".\r\n"
        self.assertTrue(lookslike_menu(menu))
        self.assertFalse(lookslike_menu("just plain text\nno tabs here\n.\r\n"))

    def test_render_menu_has_links(self):
        router = Router("localhost", 7070, fetch=fake_fetch)
        html_out = render_menu_html(router.handle(""), "home")
        self.assertIn("Gopher Ghost", html_out)
        self.assertIn("/g?", html_out)
        self.assertIn("badge", html_out)

    def test_render_text(self):
        html_out = render_text_html(text_body("hello ghost"), "t")
        self.assertIn("hello ghost", html_out)

    def test_http_roundtrip_inprocess(self):
        router = Router("localhost", 7070, fetch=fake_fetch)
        handler = make_handler("localhost", 7070, router=router)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
                body = resp.read().decode()
            self.assertIn("Hacker News", body)
            self.assertIn("--bg: #0b0614", body)
            self.assertIn("radial-gradient", body)
            # follow about via /g
            about_sel = quote("/about", safe="")
            with urlopen(
                f"http://127.0.0.1:{port}/g?t=0&s={about_sel}", timeout=5
            ) as resp:
                about = resp.read().decode()
            self.assertIn("Gopher Ghost", about)
            # web proxy
            web_sel = quote("/web?https://example.com/", safe="")
            with urlopen(
                f"http://127.0.0.1:{port}/g?t=0&s={web_sel}", timeout=5
            ) as resp:
                page = resp.read().decode()
            self.assertIn("Haunted Header", page)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
