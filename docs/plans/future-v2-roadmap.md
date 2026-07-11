# EIDP Future v2 Roadmap

Status: Future planning note
Updated: 2026-05-05

Linux/Web v1 is scoped to vocational schools and a controlled single-writer
workflow. The items below stay outside v1 so the served application can ship
without absorbing university parsing or high-concurrency platform risk.

## 1. Universities

Target: approximately 700 universities.

Why separate:

- university disclosure pages are less standardized;
- PDF layouts differ from vocational school forms;
- some universities publish HTML pages, portals, or multiple PDFs instead of a
  single form;
- matching and parser confidence need a separate gold set.

v2 work:

1. Build a university PDF/HTML gold set.
2. Add university-specific parser fixtures.
3. Extend `School.school_type` filters and UI labels.
4. Decide whether university rows share the existing Excel workbook or produce
   a separate workbook.

## 2. PostgreSQL Return Option

v1 uses SQLite because all writes are serialized by the application lock.

PostgreSQL may return when:

- multiple operators need concurrent writes;
- remote review is required;
- central backup/restore is mandatory;
- analytics queries exceed SQLite comfort.

Keep the ORM dialect-neutral where possible. SQLite-specific bootstrap should
remain isolated in `src/eidp/db/sqlite_bootstrap.py`.

## 3. Multi-Operator Support

v1.0 deliberately uses a coarse shared lock: weekly processing owns the full
workflow while UI writes pause.

A multi-operator v2 would need:

- authenticated user identity;
- finer lock granularity;
- conflict resolution for manual edits;
- audit actor attribution beyond the default operator;
- server deployment or a shared database.

## 4. Distribution Channel

v1.0 priority:

1. internal file server;
2. USB backup;
3. cloud link only as a fallback.

Future options:

- signed installer;
- internal package feed;
- automatic update checker;
- enterprise-managed allowlist for Defender / SmartScreen.

## 5. Playwright Add-On

The v1.0 core ZIP is HTTP-first and does not bundle Chromium. If future PDF
discovery requires JavaScript-heavy school sites, ship Playwright/Chromium as a
separate add-on ZIP with explicit runtime detection.

## 6. KPI Targets To Revisit

After the 5月 R8 season real run, revisit:

- new PDFs found per week;
- R8 auto-judgment success rate;
- review queue size;
- manual entry time;
- OCR success rate on image PDFs;
- HTTP success under corporate proxy/firewall;
- operator weekly time spent.

Use those observed numbers to decide whether v2 should focus first on
universities, OCR accuracy, discovery breadth, or operator workflow speed.
