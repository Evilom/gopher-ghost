import json
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gopher_ghost import client, feeds  # noqa: E402
from gopher_ghost.menu import item, parse_menu, text_body  # noqa: E402
from gopher_ghost.server import Router, Server, make_handler  # noqa: E402

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Hello ghost</title><link>https://example.com/a</link></item>
<item><title>Second</title><link>https://example.com/b</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom one</title><link href="https://example.com/x"/></entry></feed>"""


def fake_fetch(url):
    if url == feeds.HN_TOP:
        return b"[1, 2]"
    if "item/1" in url:
        return json.dumps({"id": 1, "title": "Story one", "url": "https://e.com/1",
                           "score": 10, "by": "pg", "descendants": 3}).encode()
    if "item/2" in url:
        return json.dumps({"id": 2, "title": "Story two", "score": 5, "by": "dang"}).encode()
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


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.r = Router("localhost", 7070, fetch=fake_fetch)

    def test_root(self):
        entries = parse_menu(self.r.handle(""))
        sels = [e["selector"] for e in entries]
        self.assertIn("/hn", sels)
        self.assertIn("/about", sels)

    def test_hn(self):
        entries = parse_menu(self.r.handle("/hn"))
        links = [e for e in entries if e["type"] == "h"]
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["selector"], "URL:https://e.com/1")

    def test_rss_query(self):
        entries = parse_menu(self.r.handle("/rss\thttps://example.com/feed"))
        self.assertEqual(entries[-1]["display"], "Second")

    def test_text(self):
        self.assertIn("Gopher", self.r.handle("/about"))

    def test_path_traversal_rejected(self):
        self.assertTrue(self.r.handle("/text/../../etc/passwd").startswith("3"))

    def test_not_found(self):
        self.assertTrue(self.r.handle("/nope").startswith("3"))


class LiveSocketTest(unittest.TestCase):
    def test_tcp_roundtrip(self):
        router = Router("127.0.0.1", 0, fetch=fake_fetch)
        srv = Server(("127.0.0.1", 0), make_handler(router))
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            raw = client.fetch("127.0.0.1", port, "")
            self.assertIn("Hacker News", raw)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_parse_url(self):
        self.assertEqual(client.parse_url("gopher://h:7070/0/about"), ("h", 7070, "0", "/about"))


if __name__ == "__main__":
    unittest.main()
