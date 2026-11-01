"""A minimal terminal Gopher browser.

Usage: python -m gopher_ghost.client [gopher://host:port/selector]
Commands: number = follow link, b = back, r = reload, q = quit
"""
import socket
import sys
import urllib.parse
import webbrowser

from .menu import parse_menu

TYPES = {"0": "TXT", "1": "DIR", "7": "ASK", "h": "WEB", "3": "ERR", "i": ""}


def fetch(host, port, selector, query=None, timeout=15):
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


def parse_url(url):
    u = urllib.parse.urlparse(url if "://" in url else "gopher://" + url)
    host = u.hostname or "localhost"
    port = u.port or 70
    path = u.path or ""
    itype = "1"
    if len(path) >= 2 and path[0] == "/" and path[1] in "017h":
        itype, path = path[1], path[2:]
    if u.query:
        path += "?" + u.query
    return host, port, itype, path


def render_text(raw):
    out = []
    for line in raw.splitlines():
        if line == ".":
            break
        out.append(line[1:] if line.startswith("..") else line)
    return "\n".join(out)


def run(start):
    history = []
    cur = parse_url(start)
    while True:
        host, port, itype, sel = cur
        try:
            raw = fetch(host, port, sel)
        except OSError as e:
            print(f"! connection failed: {e}")
            if not history:
                return
            cur = history.pop()
            continue
        if itype == "0":
            print(render_text(raw))
            input("-- enter to go back --")
            cur = history.pop() if history else cur
            continue
        entries = parse_menu(raw)
        links = []
        print()
        for e in entries:
            if e["type"] == "i":
                print("      " + e["display"])
            else:
                links.append(e)
                print(f"{len(links):3}) [{TYPES.get(e['type'], e['type'])}] {e['display']}")
        cmd = input("\ngopher-ghost> ").strip().lower()
        if cmd == "q":
            return
        if cmd == "b":
            cur = history.pop() if history else cur
            continue
        if cmd == "r" or not cmd.isdigit():
            continue
        n = int(cmd)
        if not 1 <= n <= len(links):
            continue
        e = links[n - 1]
        if e["type"] == "h" and e["selector"].startswith("URL:"):
            url = e["selector"][4:]
            print(f"web link: {url}")
            if input("open in browser? [y/N] ").strip().lower() == "y":
                webbrowser.open(url)
            continue
        if e["type"] == "7":
            q = input("query: ")
            raw = fetch(e["host"], e["port"], e["selector"], q)
            history.append(cur)
            # show results as a menu by re-rendering inline
            for r in parse_menu(raw):
                print(f"  [{TYPES.get(r['type'], r['type'])}] {r['display']}  {r['selector']}")
            input("-- enter to continue --")
            history.pop()
            continue
        if e["type"] in ("0", "1"):
            history.append(cur)
            cur = (e["host"], e["port"], e["type"], e["selector"])


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "gopher://localhost:7070/"
    try:
        run(start)
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
