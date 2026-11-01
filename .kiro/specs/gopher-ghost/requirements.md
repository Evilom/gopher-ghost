# Requirements: Gopher Ghost

> **初稿 / Draft, to be refined in Kiro.** This is a planning draft. Development has not been done in Kiro yet.

## Introduction
Gopher Ghost brings back the 1991 Gopher protocol (RFC 1436) and uses it to serve modern web content as text-only Gopher menus.

## Requirements

### R1: Gopher server
**User story:** As a retro-computing fan, I want to connect with any Gopher client so that I can browse Gopher Ghost.
- WHEN a client sends an empty selector THEN the server SHALL return the root menu that ends with `.`
- WHEN a selector is unknown THEN the server SHALL return a type-3 error item
- The port SHALL be configurable. The default is 7070, and 70 is supported.

### R2: Hacker News
- WHEN a client requests `/hn` THEN the server SHALL list the top 15 stories as type-h links with score, author, and comment count
- HN responses SHALL be cached for at least 5 minutes

### R3: RSS/Atom
- WHEN a client submits a feed URL through a type-7 query THEN the server SHALL return the feed's entries as a menu
- Only http(s) URLs SHALL be accepted

### R4: Text pages
- Text pages SHALL be served as type 0 with dot-stuffing
- Path traversal outside `content/` SHALL be rejected

### R5: Terminal client
- The user SHALL be able to open a gopher:// URL, follow numbered links, go back, and quit

### R6 (planned): Web-to-Gopher proxy and HTTP gateway for judges
