# Discovery Gold Set

This directory records manual or Codex-assisted demonstrations for finding a
school's public confirmation PDF before turning the path into crawler logic.

The goal is to stop treating discovery as broad blind crawling. Each entry
captures:

- what the operator or Codex tried,
- which page or PDF proved useful,
- which clues made the result reusable,
- whether the result is true target-year success or only the latest public
  stale-year form.

`entries/*.json` are intentionally small and append-only. A future discovery
agent should learn from these demonstrations, then emit structured candidates
that can be compared with this gold set.
