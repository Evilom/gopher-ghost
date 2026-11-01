# Design: Gopher Ghost

> **初稿 / Draft, to be refined in Kiro.** This is a planning draft. Development has not been done in Kiro yet.

## Architecture
```
Gopher client --TCP--> server.Router --> feeds (HN API / RSS) --> menu builder --> response
```
- **server.py**: `socketserver.ThreadingMixIn` TCP server. It reads one selector line and routes it with `Router.handle`.
- **menu.py**: RFC 1436 line formatting (`type display TAB selector TAB host TAB port CRLF`), dot-stuffing, and parsing.
- **feeds.py**: urllib fetch with an in-memory TTL cache, the HN Firebase API, and an RSS 2.0/Atom parser (ElementTree).
- **client.py**: socket fetch and a numbered-menu REPL.

## Decisions
- Standard library only, so it runs anywhere with Python 3.9+.
- `fetch` can be injected into Router, so tests never touch the network.
- Web links use the de-facto `URL:` selector convention with type `h`.

## Open questions (resolve in Kiro)
- Which HTML-to-text approach to use for the proxy?
- Should the HTTP gateway be a separate process or the same one?
