# Technical Direction

EIDP v1 is a Python 3.12 Linux/Web data application. Python remains the domain
core and Streamlit remains the current browser UI while the workflow is served
inside the campus network.

## Current stack

| Layer | v1 direction |
| --- | --- |
| Domain/pipeline | Python, Pydantic, deterministic extraction |
| Persistence | SQLAlchemy + SQLite, POSIX single-writer lock |
| PDF/OCR | pdfplumber/PyMuPDF; OCR optional and explicitly routed |
| Excel | openpyxl import/export and read-only master diff |
| Web UI | Streamlit, loopback-bound behind an internal reverse proxy |
| Deployment | `uv` project `.venv` under `/home/junming/EIDP` |

## Architecture boundary

Users do not SSH into the application or edit server files. They use the Web
workflow for intake, review, comparison, and download. All application files on
Venus remain inside `/home/junming/EIDP`.

## Evolution triggers

FastAPI/React/PostgreSQL are target options, not v1 prerequisites. Reconsider
them only when measured use requires concurrent editors, roles, durable job
queues, or row-level transaction control that the current single-writer model
cannot safely provide.

Automatic discovery remains available as support tooling. It must not replace
the human-confirmed-PDF product boundary or block the Linux/Web release.
