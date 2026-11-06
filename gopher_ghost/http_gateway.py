"""HTTP gateway so judges can browse Gopher Ghost without a Gopher client.

Usage: python -m gopher_ghost.http_gateway [--port 8080]
         [--gopher-host localhost] [--gopher-port 7070]

Or run a built-in in-process router (no separate Gopher server needed):
  python -m gopher_ghost.http_gateway --in-process --port 8080
"""
import argparse
import html
import os
import socket
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .menu import parse_menu
from .server import Router

GHOST = r"""
<pre class="ghost">
      .-.
     (o o)   Gopher Ghost
      |O|    HTTP gateway
     '~~~'   Kiroween 2026
</pre>
"""

CSS = """
:root { color-scheme: dark; }
body {
  margin: 0; padding: 1.5rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #0b0614; color: #e8d5ff;
  line-height: 1.45;
}
a { color: #c9a0ff; text-decoration: none; border-bottom: 1px dotted #6b3fa0; }
a:hover { color: #fff; border-bottom-color: #e8d5ff; }
h1 { font-size: 1.1rem; font-weight: normal; color: #b388ff; }
.ghost { color: #9b7bb8; margin: 0 0 1rem 0; }
.info { color: #8a7a9a; white-space: pre-wrap; margin: 0.1rem 0; }
.menu { list-style: none; padding: 0; margin: 0.5rem 0 1.5rem; }
.menu li { margin: 0.35rem 0; }
.badge {
  display: inline-block; min-width: 2.4rem;
  color: #0b0614; background: #9b7bb8;
  padding: 0 0.35rem; margin-right: 0.5rem;
  border-radius: 2px; font-size: 0.75rem;
}
.text {
  white-space: pre-wrap; background: #140a22;
  border: 1px solid #3a2458; padding: 1rem; border-radius: 4px;
}
.err { color: #ff8a80; }
.foot { margin-top: 2rem; color: #6a5a7a; font-size: 0.85rem; }
form { margin: 1rem 0; }
input[type=text] {
  width: min(40rem, 90%); background: #140a22; color: #e8d5ff;
  border: 1px solid #6b3fa0; padding: 0.4rem 0.6rem;
}
button {
  background: #6b3fa0; color: #fff; border: 0; padding: 0.45rem 0.8rem;
  cursor: pointer; margin-left: 0.4rem;
}
"""

TYPE_LABEL = {
    "0": "TXT",
    "1": "DIR",
    "7": "ASK",
    "h": "WEB",
    "3": "ERR",
    "i": "···",
}


def gopher_fetch(host, port, selector, query=None, timeout=20):
    line = selector + (("\t" + query) if query else "") + "\r\n"
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(line.encode("utf-8"))
        chunks = []
        while True:
            data = s.recv(65536)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode("utf-8", "replace")


def lookslike_menu(raw):
    """Heuristic: menus have tab-separated fields; text bodies usually do not."""
    lines = [ln for ln in raw.splitlines() if ln and ln != "."]
    if not lines:
        return False
    sample = lines[: min(8, len(lines))]
    tabs = sum(1 for ln in sample if "\t" in ln and len(ln) > 1)
    return tabs >= max(1, len(sample) // 2)


def render_text_html(raw, title="text"):
    # strip terminating period / dot-stuffing
    out = []
    for line in raw.splitlines():
        if line == ".":
            break
        out.append(line[1:] if line.startswith("..") else line)
    body = html.escape("\n".join(out))
    return page(title, f'<div class="text">{body}</div>')


def href_for_entry(entry):
    itype = entry["type"]
    sel = entry["selector"]
    if itype == "h" and sel.startswith("URL:"):
        return sel[4:], True  # external
    if itype in ("0", "1", "7", "3"):
        # encode selector for our /g path
        q = urllib.parse.quote(sel, safe="")
        return f"/g?t={itype}&s={q}", False
    return None, False


def render_menu_html(raw, title="menu"):
    entries = parse_menu(raw)
    items = []
    search_forms = []
    for e in entries:
        itype = e["type"]
        if itype == "i":
            items.append(f'<p class="info">{html.escape(e["display"])}</p>')
            continue
        label = TYPE_LABEL.get(itype, itype)
        disp = html.escape(e["display"])
        if itype == "7":
            # inline search form posting to /g with query
            sel_q = urllib.parse.quote(e["selector"], safe="")
            form = (
                f'<li><span class="badge">{label}</span>{disp}'
                f'<form method="get" action="/g">'
                f'<input type="hidden" name="t" value="7"/>'
                f'<input type="hidden" name="s" value="{html.escape(e["selector"])}"/>'
                f'<input type="text" name="q" placeholder="enter URL or query"/>'
                f'<button type="submit">go</button></form></li>'
            )
            items.append(form)
            continue
        href, external = href_for_entry(e)
        if not href:
            items.append(
                f'<li><span class="badge">{label}</span>{disp}</li>'
            )
            continue
        target = ' target="_blank" rel="noopener"' if external else ""
        items.append(
            f'<li><span class="badge">{label}</span>'
            f'<a href="{html.escape(href)}"{target}>{disp}</a></li>'
        )
    body = GHOST + f"<h1>{html.escape(title)}</h1><ul class=\"menu\">" + "".join(items) + "</ul>"
    body += (
        '<div class="foot">'
        '<a href="/">home</a> · '
        "Gopher Ghost HTTP gateway · black/purple haunted theme"
        "</div>"
    )
    return page(title, body)


def page(title, body_inner):
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        f"<meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>"
        f"<title>{html.escape(title)} · Gopher Ghost</title>"
        f"<style>{CSS}</style></head><body>{body_inner}</body></html>"
    )


def make_handler(gopher_host, gopher_port, router=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[http] {self.address_string()} {fmt % args}")

        def _send(self, code, body, content_type="text/html; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path or "/"
            qs = urllib.parse.parse_qs(parsed.query)

            if path in ("/", "/index.html"):
                raw = self._fetch("")
                return self._send(200, render_menu_html(raw, "Gopher Ghost"))

            if path == "/g":
                itype = (qs.get("t") or ["1"])[0]
                sel = (qs.get("s") or [""])[0]
                query = (qs.get("q") or [None])[0]
                # URL: redirect handled as external already; still allow
                if sel.startswith("URL:"):
                    self.send_response(302)
                    self.send_header("Location", sel[4:])
                    self.end_headers()
                    return
                raw = self._fetch(sel, query=query if itype == "7" else None)
                if itype == "0" or (itype != "1" and itype != "7" and not lookslike_menu(raw)):
                    # type 0 text, or URL: HTML passthrough
                    if raw.lstrip().lower().startswith("<html"):
                        return self._send(200, raw)
                    return self._send(200, render_text_html(raw, sel or "text"))
                return self._send(200, render_menu_html(raw, sel or "menu"))

            if path == "/raw":
                sel = (qs.get("s") or [""])[0]
                raw = self._fetch(sel)
                return self._send(200, raw, "text/plain; charset=utf-8")

            self._send(
                404,
                page("404", '<p class="err">Not found. <a href="/">home</a></p>'),
            )

        def _fetch(self, selector, query=None):
            if router is not None:
                # in-process: type-7 query is selector\tquery
                sel = selector
                if query:
                    sel = selector + "\t" + query
                return router.handle(sel)
            return gopher_fetch(gopher_host, gopher_port, selector, query=query)

    return Handler


def serve(
    host="0.0.0.0",
    port=8080,
    gopher_host="localhost",
    gopher_port=7070,
    in_process=False,
    public_host=None,
):
    router = None
    if in_process:
        pub = public_host or ("localhost" if host in ("0.0.0.0", "") else host)
        router = Router(pub, gopher_port)
        print(f"HTTP gateway (in-process router) on http://{pub}:{port}/")
    else:
        print(
            f"HTTP gateway on http://{host}:{port}/ → gopher://{gopher_host}:{gopher_port}/"
        )
    handler = make_handler(gopher_host, gopher_port, router=router)
    with ThreadingHTTPServer((host, port), handler) as httpd:
        httpd.serve_forever()


def main():
    p = argparse.ArgumentParser(description="Gopher Ghost HTTP gateway")
    p.add_argument("--host", default=os.environ.get("GHOST_HTTP_HOST", "0.0.0.0"))
    p.add_argument(
        "--port", type=int, default=int(os.environ.get("GHOST_HTTP_PORT", "8080"))
    )
    p.add_argument(
        "--gopher-host",
        default=os.environ.get("GOPHER_PUBLIC_HOST")
        or os.environ.get("GOPHER_HOST", "localhost"),
    )
    p.add_argument(
        "--gopher-port",
        type=int,
        default=int(os.environ.get("GOPHER_PORT", "7070")),
    )
    p.add_argument(
        "--in-process",
        action="store_true",
        help="Use in-process Router (no separate Gopher server)",
    )
    p.add_argument("--public-host", default=os.environ.get("GOPHER_PUBLIC_HOST"))
    a = p.parse_args()
    # if gopher host was 0.0.0.0, talk to localhost
    gh = a.gopher_host
    if gh in ("0.0.0.0", ""):
        gh = "localhost"
    serve(
        a.host,
        a.port,
        gh,
        a.gopher_port,
        in_process=a.in_process,
        public_host=a.public_host,
    )


if __name__ == "__main__":
    main()
