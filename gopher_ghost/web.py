"""Fetch a web page and flatten it to readable plain text for Gopher type 0."""
import html.parser
import re
import urllib.error
import urllib.parse
import urllib.request

from .feeds import UA

MAX_BYTES = 512_000
FETCH_TIMEOUT = 12
MAX_CHARS = 80_000


class _HTMLToText(html.parser.HTMLParser):
    """Minimal tag stripper: keep text, collapse whitespace, preserve breaks."""

    BLOCK = {
        "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
        "blockquote", "pre", "section", "article", "header", "footer", "nav",
        "ul", "ol", "table", "hr", "figcaption",
    }
    SKIP = {"script", "style", "noscript", "template", "svg", "iframe"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = True
        if tag == "br":
            self.parts.append("\n")
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.parts.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP:
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self._title += data
            return
        self.parts.append(data)

    def text(self):
        raw = "".join(self.parts)
        # collapse runs of spaces/tabs but keep newlines
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r" *\n *", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
        return raw


def sanitize_url(url):
    """Accept only http(s); reject empty, weird schemes, credentials in netloc."""
    url = (url or "").strip()
    if not url:
        raise ValueError("empty URL")
    # Reject obvious non-http schemes even when written without "//"
    # (e.g. javascript:alert(1), data:text/html,...).
    lowered = url.lower()
    if lowered.startswith(("javascript:", "data:", "file:", "vbscript:", "about:")):
        scheme = lowered.split(":", 1)[0]
        raise ValueError(f"blocked scheme: {scheme}")
    if "://" not in url:
        # bare host/path → assume https
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            scheme = url.split(":", 1)[0]
            raise ValueError(f"blocked scheme: {scheme}")
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme: {parsed.scheme or '(none)'}")
    if not parsed.hostname:
        raise ValueError("missing host")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URL are not allowed")
    # rebuild without fragment
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, "")
    )


def html_to_text(html_bytes, charset="utf-8"):
    if isinstance(html_bytes, bytes):
        # honor charset sniff lightly
        try:
            text = html_bytes.decode(charset, "replace")
        except LookupError:
            text = html_bytes.decode("utf-8", "replace")
    else:
        text = html_bytes
    parser = _HTMLToText()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        # broken HTML still often yields partial text
        pass
    body = parser.text()
    title = re.sub(r"\s+", " ", parser._title).strip()
    if title:
        return f"{title}\n{'=' * min(len(title), 70)}\n\n{body}"
    return body


def fetch_page(url, fetch=None, max_bytes=MAX_BYTES, timeout=FETCH_TIMEOUT):
    """Return plain text for a page. Uses injectable fetch for tests."""
    url = sanitize_url(url)
    if fetch is None:
        # dedicated fetch with size cap (feeds._get caches freely; pages can be big)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            data = resp.read(max_bytes + 1)
            charset = "utf-8"
            if "charset=" in ctype.lower():
                charset = ctype.lower().split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    else:
        data = fetch(url)
        charset = "utf-8"
        ctype = "text/html"
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    else:
        truncated = False
    # if clearly not HTML/text, say so
    if isinstance(data, bytes) and data[:2] == b"\x1f\x8b":
        raise ValueError("gzip/binary content not supported")
    text = html_to_text(data, charset=charset)
    if truncated:
        text += "\n\n[... truncated by Gopher Ghost ...]"
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[... truncated by Gopher Ghost ...]"
    header = f"Source: {url}\nFetched by Gopher Ghost (web → gopher text)\n\n"
    return header + text
