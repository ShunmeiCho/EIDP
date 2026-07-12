from pathlib import Path


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_linux_web_is_the_only_v1_product_definition() -> None:
    adr = _text("docs/decisions/ADR-2026-07-linux-web-pivot.md")
    rules = _text("CLAUDE.md")

    assert "Status: **Accepted for implementation by project directive; PI ratification pending**" in adr
    assert "does not satisfy release sign-off" in adr
    assert "Windows single-machine runtime" in adr
    assert "retired from `main`" in adr
    assert "Single mainline: `main`" in rules


def test_release_gate_is_served_app_not_automatic_discovery_yield() -> None:
    gates = _text("docs/governance/release-gates.md")

    assert "G1 — served application" in gates
    assert "support-only" in gates
    assert "do not determine Linux/Web v1 release readiness" in gates


def test_exit_criteria_require_venus_and_business_lan_evidence() -> None:
    criteria = _text("docs/release/v1-exit-criteria.md")

    assert "/home/junming/EIDP/.venv" in criteria
    assert "authorized business PC" in criteria
    assert "Automatic target-year discovery yield is monitored but is not an exit gate" in criteria


def test_current_release_status_stays_not_ready_until_deployment_evidence() -> None:
    status = _text("docs/reports/current-release-status.md")

    assert "Release Forecast: `NOT_READY`" in status
    assert "Venus install/start/restart" in status
    assert "LAN accessibility" in status
