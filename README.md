# 👻 Gopher Ghost

**Kiroween 2026 hackathon entry. Category: Resurrection.**

> This repository is the starting point for a Kiroween 2026 entry. I plan to keep developing it in **Kiro**.
> The files under `.kiro/` are **draft plans** (specs, steering, hooks) that I will refine in Kiro.
> They are not a record of finished Kiro work. Local demo commits are temporary scaffolding until the official Kiro build path catches up.

Gopher Ghost brings back the **Gopher protocol** (University of Minnesota, 1991; [RFC 1436](https://datatracker.ietf.org/doc/html/rfc1436)).
The web replaced Gopher. Now Gopher Ghost uses it to show the modern web: Hacker News,
any RSS/Atom feed, and plain text pages, all as fast, ad-free, text-only Gopher menus.

## What works today (demo v1)

- **Gopher server** (`gopher_ghost/server.py`): pure Python standard library, threaded
  - `/`: haunted root menu (ASCII ghost + spooky type-`i` lines)
  - `/hn`: live Hacker News top stories (cached ~5 minutes)
  - `/hn/<id>`: HN story / comment thread as nested Gopher menus
  - `/rss`: type-7 search — enter any RSS/Atom URL (`/rss?<url>` also works)
  - `/web`: type-7 search — fetch a web page, strip HTML → readable type-0 text (`/web?<url>`, `/page/<encoded>`)
  - `/about` and `/text/<name>.txt`: text pages from `content/`, with correct dot-stuffing
  - `URL:` selectors: the standard convention for links out to the web
- **HTTP gateway** (`gopher_ghost/http_gateway.py`): haunted black/purple HTML so judges can click menus in a browser
- **Terminal client** (`gopher_ghost/client.py`): a tiny interactive browser for any Gopher server
- **Tests** (`tests/`): unit tests plus real TCP / HTTP round-trips (no live network required)

## Run it

Requires Python 3.9+. **No pip dependencies** (stdlib only).

```bash
# Gopher server (port 70 is canonical but needs root; default is 7070)
python3 -m gopher_ghost.server --port 7070

# HTTP gateway for browsers / judges (proxies the Gopher server)
python3 -m gopher_ghost.http_gateway --port 8080 --gopher-host localhost --gopher-port 7070

# Or one process only (in-process router, no separate Gopher port needed)
python3 -m gopher_ghost.http_gateway --in-process --port 8080

# Terminal client
python3 -m gopher_ghost.client gopher://localhost:7070/

# Classic curl against Gopher
curl gopher://localhost:7070/
curl gopher://localhost:7070/1/hn
curl "gopher://localhost:7070/0/web?https://example.com/"

# Browser
open http://localhost:8080/

# Tests
python3 -m unittest discover -s tests -v
```

Options: `--host`, `--port`, `--public-host` (hostname written into menu links).
Env: `GOPHER_HOST`, `GOPHER_PORT`, `GOPHER_PUBLIC_HOST`, `GOPHER_GHOST_CONTENT`,
`GHOST_HTTP_HOST`, `GHOST_HTTP_PORT`.

## Research & related work

Useful references while resurrecting Gopher:

| Resource | Why it matters |
| --- | --- |
| [RFC 1436 – The Internet Gopher Protocol](https://datatracker.ietf.org/doc/html/rfc1436) | The original 1993 spec (selectors, types `0`/`1`/`7`, dot termination). |
| [Floodgap Gopher](https://gopher.floodgap.com/) ([gopher://gopher.floodgap.com](gopher://gopher.floodgap.com/)) | Long-running public Gopher hole + HTTP proxy to explore classic gopherspace. |
| [gopher-rss-proxy](https://github.com/MortenHarding/gopher-rss-proxy) | Prior art for exposing RSS as Gopher menus. |
| [proxy70](https://github.com/beebeeep/proxy70) | HTTP→Gopher proxy ideas for letting browsers reach Gopher servers. |
| [SmolNet Portal](https://portal.mozz.us/about) ([repo](https://github.com/michael-lazar/smolnet-portal)) | Modern “small net” portal (Gopher/Gemini) — UX inspiration for text-first browsing. |
| [gopher-cli](https://github.com/penserai/gopher-cli) | Terminal Gopher client reference. |
| [Dillo+](https://github.com/crossbowerbt/dillo-plus) | Lightweight browser with Gopher support — good for judging demos without curl. |

## Still planned (prefer building these in Kiro)

- [ ] Gophermap files for user-defined menus
- [ ] Search (type 7) across cached feeds
- [ ] Docker image and a one-command deploy
- [ ] Curses UI for the client (bookmarks, history)
- [ ] Public demo deploy + Devpost write-up / demo video

Already landed in this local demo (mark formally done when replaying in Kiro): web→Gopher text, HN comment menus, haunted theme, HTTP gateway.

## Project layout

```
gopher_ghost/   server, http_gateway, client, menu, feeds, web
content/        static text pages
tests/          unittest suite
.kiro/          draft specs / steering / hooks (to be refined in Kiro)
```

## License

MIT. See [LICENSE](LICENSE).
