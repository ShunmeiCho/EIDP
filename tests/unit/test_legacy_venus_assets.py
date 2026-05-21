from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REDISCOVERY_METHODS = (
    "prefecture_aggregator",
    "seed_csv",
    "corporation_pattern",
    "school_domain_override",
    "operator_manual",
    "scrapling_stealth",
)


def _read_repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_legacy_cron_wrapper_uses_current_method_set_by_default() -> None:
    text = _read_repo_text("deploy/legacy-venus/run_r8_rediscovery_cron.sh")

    assert "EIDP_REDISCOVERY_METHODS" in text
    assert " ".join(DEFAULT_REDISCOVERY_METHODS) in text
    assert '--methods "${REDISCOVERY_METHODS[@]}"' in text
    assert "--methods prefecture_aggregator \\" not in text


def test_legacy_systemd_unit_uses_current_method_set() -> None:
    text = _read_repo_text("deploy/legacy-venus/systemd/eidp-r8-rediscovery.service")

    exec_start = next(line for line in text.splitlines() if line.startswith("ExecStart="))
    assert f"--methods {' '.join(DEFAULT_REDISCOVERY_METHODS)} --current-fy" in exec_start
    assert "--methods prefecture_aggregator --current-fy" not in exec_start
