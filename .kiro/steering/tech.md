---
inclusion: always
---
# Tech

> **初稿 / Draft, to be refined in Kiro.** This is a planning draft. Development has not been done in Kiro yet.

- Python 3.9+, **standard library only** unless there is a strong reason
- Follow RFC 1436: CRLF line endings, a `.` terminator, and dot-stuffing
- Tests: `python3 -m unittest discover -s tests`. Tests must not hit the network; inject `fetch` instead.
- Run: `python3 -m gopher_ghost.server --port 7070`
