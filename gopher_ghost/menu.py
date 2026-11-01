"""Helpers for building Gopher menus (RFC 1436)."""

TAB = "\t"
CRLF = "\r\n"


def item(itype, display, selector="", host="null.host", port=0):
    """One menu line: <type><display>\t<selector>\t<host>\t<port>"""
    display = display.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    selector = selector.replace("\t", " ").replace("\r", "").replace("\n", "")
    return f"{itype}{display}{TAB}{selector}{TAB}{host}{TAB}{port}{CRLF}"


def info(text):
    """Informational (type i) line; widely supported de-facto extension."""
    return item("i", text, "", "null.host", 0)


def end():
    return "." + CRLF


def text_body(text):
    """Type 0 text body with dot-stuffing and terminating period."""
    lines = []
    for line in text.splitlines():
        if line.startswith("."):
            line = "." + line
        lines.append(line)
    return CRLF.join(lines) + CRLF + end()


def parse_menu(raw):
    """Parse a menu response into a list of dicts (used by the client)."""
    entries = []
    for line in raw.splitlines():
        line = line.rstrip("\r")
        if line == "." or not line:
            if line == ".":
                break
            continue
        itype, rest = line[0], line[1:]
        parts = rest.split("\t")
        while len(parts) < 4:
            parts.append("")
        display, selector, host, port = parts[:4]
        try:
            port = int(port)
        except ValueError:
            port = 0
        entries.append({"type": itype, "display": display, "selector": selector,
                        "host": host, "port": port})
    return entries
