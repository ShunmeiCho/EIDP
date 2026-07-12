# Goal Execution

Work is planned and reviewed against the Linux/Web product definition in
`CLAUDE.md` and the release gates in `docs/governance/release-gates.md`.

## Rules

1. `main` is the only development line.
2. A task is complete only when its user-visible outcome and relevant tests are
   complete; green code without deployment evidence is not a release.
3. Preserve append-only revisions, audit identity, master.xlsx read-only use,
   and the shared SQLite writer lock.
4. Automatic discovery metrics are support signals and cannot reintroduce the
   retired Windows product definition.
5. All Venus operations remain below `/home/junming/EIDP` and use the project
   virtual environment.
6. Release claims require fresh source-quality, served-app, LAN-browser,
   security, and backup/restore evidence.

## Checkpoint format

At each material checkpoint record:

- what changed;
- what was freshly verified;
- what remains unverified or blocked;
- which G1-G15 goals the work advances.

Do not hide skipped checks or turn an unmeasured condition into PASS.
