# 👻 Gopher Ghost

**Kiroween 2026 hackathon entry. Category: Resurrection.**

> This repository is the starting point for a Kiroween 2026 entry. I plan to keep developing it in **Kiro**.
> The files under `.kiro/` are **draft plans** (specs, steering, hooks) that I will refine in Kiro.
> They are not a record of finished Kiro work.

Gopher Ghost brings back the **Gopher protocol** (University of Minnesota, 1991; RFC 1436).
The web replaced Gopher. Now Gopher Ghost uses it to show the modern web: Hacker News,
any RSS/Atom feed, and plain text pages, all as fast, ad-free, text-only Gopher menus.

## What works today

- **Gopher server** (`gopher_ghost/server.py`): pure Python standard library, threaded, with a configurable port
  - `/`: root menu
  - `/hn`: live Hacker News top stories (cached for 5 minutes)
  - `/rss`: type-7 search item. Enter any RSS/Atom URL and get it back as a menu. `/rss?<url>` also works.
  - `/about` and `/text/<name>.txt`: text pages from `content/`, with correct dot-stuffing
  - `URL:` selectors: the standard convention for links out to the web
- **Terminal client** (`gopher_ghost/client.py`): a tiny interactive browser for any Gopher server
- **Tests** (`tests/`): unit tests plus a real TCP round-trip, with no network needed

## Run it

Requires Python 3.9+. No dependencies.

```bash
# server (port 70 is canonical but needs root, so the default is 7070)
python3 -m gopher_ghost.server --port 7070
# or: GOPHER_PORT=70 sudo -E python3 -m gopher_ghost.server

# client, in another terminal
python3 -m gopher_ghost.client gopher://localhost:7070/

# or use any classic client
curl gopher://localhost:7070/
curl gopher://localhost:7070/1/hn

# tests
python3 -m unittest discover -s tests -v
```

Options: `--host`, `--port`, and `--public-host` (the hostname written into menu links). You can also set `GOPHER_HOST`, `GOPHER_PORT`, `GOPHER_PUBLIC_HOST`, and `GOPHER_CONTENT`.

## Planned features (to be built in Kiro)

- [ ] Web-to-Gopher proxy: fetch any web page, strip it to readable text, and serve it as type 0
- [ ] HN comment threads as nested menus
- [ ] Spooky "haunted" theme: ASCII art and a ghost guide in the menus
- [ ] Gophermap files for user-defined menus
- [ ] Search (type 7) across cached feeds
- [ ] Optional HTTP gateway so judges can try it in a browser
- [ ] Docker image and a one-command deploy
- [ ] Curses UI for the client (bookmarks, history)

## Project layout

```
gopher_ghost/   server, client, menu helpers, feed fetchers
content/        static text pages
tests/          unittest suite
.kiro/          draft specs / steering / hooks (to be refined in Kiro)
```

## License

MIT. See [LICENSE](LICENSE).
