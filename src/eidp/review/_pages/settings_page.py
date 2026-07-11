"""Streamlit page: operator/admin settings.

The project is long-lived, so operational variables must not be hidden in
scripts or source code. This page edits the small set of variables that affect
annual operation and official-page search.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session

from eidp.config import (
    MAX_SUPPORTED_TARGET_FISCAL_YEAR,
    MIN_SUPPORTED_TARGET_FISCAL_YEAR,
    apply_fiscal_era_settings,
    apply_runtime_env_settings,
    settings,
)
from eidp.db.audit import log_manual_action
from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import ManualActionLog
from eidp.fiscal_year import JapaneseEra, format_fiscal_year_label
from eidp.pipeline.school_fiscal_year_status import (
    SchoolFiscalYearStatusStats,
    rebuild_school_fiscal_year_status,
)

SETTING_ENV_KEYS = (
    "EIDP_FISCAL_ERA_ENABLED",
    "EIDP_FISCAL_ERA_NAME",
    "EIDP_FISCAL_ERA_ROMANIZED",
    "EIDP_FISCAL_ERA_INITIAL",
    "EIDP_FISCAL_ERA_START_YEAR",
    "EIDP_OCR_AUTO_ENABLE",
    "EIDP_OCR_MIN_CPUS",
    "EIDP_OCR_MIN_FREE_RAM_MB",
    "EIDP_TESSERACT_BIN",
    "EIDP_OCR_PROVIDER",
    "EIDP_OCR_DEVICE",
    "EIDP_SEARCH_PROVIDER",
    "EIDP_URL_SEARCH_AUTO_ENABLE",
    "EIDP_URL_SEARCH_BATCH_SIZE",
    "EIDP_SERPER_API_KEY",
    "EIDP_BRAVE_API_KEY",
    "EIDP_GOOGLE_API_KEY",
    "EIDP_GOOGLE_CX",
    "EIDP_FIRECRAWL_API_KEY",
)

BUILD_INFO_DISPLAY_KEYS = (
    "git_commit",
    "git_branch",
    "built_at_utc",
    "git_dirty",
)

SECRET_SETTING_ENV_KEYS = frozenset(
    {
        "EIDP_SERPER_API_KEY",
        "EIDP_BRAVE_API_KEY",
        "EIDP_GOOGLE_API_KEY",
        "EIDP_FIRECRAWL_API_KEY",
    }
)


def _bool_to_env(value: bool) -> str:
    return "true" if value else "false"


def _clean_romanized(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", value.strip().lower())


def update_env_text(text: str, updates: dict[str, str]) -> str:
    """Return ``.env`` text with selected keys updated or appended.

    This deliberately handles only simple ``KEY=value`` lines, which is enough
    for EIDP's operator settings and preserves unrelated comments/variables.
    """
    seen: set[str] = set()
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        key = stripped.split("=", 1)[0] if "=" in stripped and not stripped.startswith("#") else ""
        if key in updates:
            lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            lines.append(line)

    missing = [key for key in updates if key not in seen]
    if missing:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# EIDP operator settings")
        for key in missing:
            lines.append(f"{key}={updates[key]}")
    return "\n".join(lines).rstrip() + "\n"


def save_operator_settings(
    env_path: Path,
    *,
    target_fiscal_year: int,
    fiscal_era_enabled: bool,
    fiscal_era_name: str,
    fiscal_era_romanized: str,
    fiscal_era_initial: str,
    fiscal_era_start_year: int,
    ocr_auto_enable: str,
    ocr_min_cpus: int,
    ocr_min_free_ram_mb: int,
    tesseract_bin: str,
    ocr_provider: str,
    ocr_device: str,
    search_provider: str,
    url_search_auto_enable: str,
    url_search_batch_size: int,
    serper_api_key: str,
    brave_api_key: str,
    google_api_key: str,
    google_cx: str,
    firecrawl_api_key: str,
) -> dict[str, str]:
    """Persist operator settings to ``.env`` and current process settings.

    The target fiscal year is intentionally current-process only so the annual
    rollover is not pinned by a saved operator setting.
    """
    updates = {
        "EIDP_FISCAL_ERA_ENABLED": _bool_to_env(fiscal_era_enabled),
        "EIDP_FISCAL_ERA_NAME": fiscal_era_name.strip(),
        "EIDP_FISCAL_ERA_ROMANIZED": _clean_romanized(fiscal_era_romanized),
        "EIDP_FISCAL_ERA_INITIAL": _clean_romanized(fiscal_era_initial)[:1],
        "EIDP_FISCAL_ERA_START_YEAR": str(fiscal_era_start_year),
        "EIDP_OCR_AUTO_ENABLE": ocr_auto_enable,
        "EIDP_OCR_MIN_CPUS": str(ocr_min_cpus),
        "EIDP_OCR_MIN_FREE_RAM_MB": str(ocr_min_free_ram_mb),
        "EIDP_TESSERACT_BIN": tesseract_bin.strip(),
        "EIDP_OCR_PROVIDER": ocr_provider.strip().lower(),
        "EIDP_OCR_DEVICE": ocr_device.strip().lower(),
        "EIDP_SEARCH_PROVIDER": search_provider,
        "EIDP_URL_SEARCH_AUTO_ENABLE": url_search_auto_enable,
        "EIDP_URL_SEARCH_BATCH_SIZE": str(url_search_batch_size),
        "EIDP_SERPER_API_KEY": serper_api_key.strip(),
        "EIDP_BRAVE_API_KEY": brave_api_key.strip(),
        "EIDP_GOOGLE_API_KEY": google_api_key.strip(),
        "EIDP_GOOGLE_CX": google_cx.strip(),
        "EIDP_FIRECRAWL_API_KEY": firecrawl_api_key.strip(),
    }
    current = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    env_path.write_text(update_env_text(current, updates), encoding="utf-8")

    for key, value in updates.items():
        os.environ[key] = value

    settings.target_fiscal_year = target_fiscal_year
    settings.fiscal_era_enabled = fiscal_era_enabled
    settings.fiscal_era_name = updates["EIDP_FISCAL_ERA_NAME"]
    settings.fiscal_era_romanized = updates["EIDP_FISCAL_ERA_ROMANIZED"]
    settings.fiscal_era_initial = updates["EIDP_FISCAL_ERA_INITIAL"]
    settings.fiscal_era_start_year = fiscal_era_start_year
    apply_fiscal_era_settings(settings)

    settings.ocr_auto_enable = updates["EIDP_OCR_AUTO_ENABLE"]
    settings.ocr_min_cpus = ocr_min_cpus
    settings.ocr_min_free_ram_mb = ocr_min_free_ram_mb
    settings.tesseract_bin = updates["EIDP_TESSERACT_BIN"]
    settings.ocr_provider = updates["EIDP_OCR_PROVIDER"]
    settings.ocr_device = updates["EIDP_OCR_DEVICE"]
    settings.search_provider = updates["EIDP_SEARCH_PROVIDER"]
    settings.url_search_auto_enable = updates["EIDP_URL_SEARCH_AUTO_ENABLE"]
    settings.url_search_batch_size = url_search_batch_size
    settings.serper_api_key = updates["EIDP_SERPER_API_KEY"]
    settings.brave_api_key = updates["EIDP_BRAVE_API_KEY"]
    settings.google_api_key = updates["EIDP_GOOGLE_API_KEY"]
    settings.google_cx = updates["EIDP_GOOGLE_CX"]
    settings.firecrawl_api_key = updates["EIDP_FIRECRAWL_API_KEY"]
    apply_runtime_env_settings(settings)
    return updates


def _audit_setting_value(key: str, value: str) -> str:
    if key in SECRET_SETTING_ENV_KEYS:
        return "[set]" if value else ""
    return value


def audit_operator_settings_saved(
    session: Session,
    *,
    old_target_fiscal_year: int,
    target_fiscal_year: int,
    updates: dict[str, str],
    rebuild_stats: SchoolFiscalYearStatusStats | None,
    actor: str = "operator",
) -> ManualActionLog:
    """Audit a successful operator settings save without exposing secrets."""
    new_value: dict[str, object] = {
        "target_fiscal_year": int(target_fiscal_year),
        "settings": {key: _audit_setting_value(key, value) for key, value in sorted(updates.items())},
    }
    if rebuild_stats is not None:
        new_value["school_year_status_rebuild"] = {
            "fiscal_year": rebuild_stats.fiscal_year,
            "school_type": rebuild_stats.school_type,
            "rebuilt": rebuild_stats.rebuilt,
            "excel_ready": rebuild_stats.excel_ready,
        }

    return log_manual_action(
        session,
        action_type="operator_settings_saved",
        target_table="operator_settings",
        old_value={"target_fiscal_year": int(old_target_fiscal_year)},
        new_value=new_value,
        reason="Operator saved runtime settings",
        actor=actor,
    )


def maybe_rebuild_school_year_tasks_after_target_change(
    session: Session,
    *,
    old_target_fiscal_year: int,
    target_fiscal_year: int,
) -> SchoolFiscalYearStatusStats | None:
    """Rebuild the operator task table when the operational year changes."""
    if int(old_target_fiscal_year) == int(target_fiscal_year):
        return None
    return rebuild_school_fiscal_year_status(
        session,
        fiscal_year=int(target_fiscal_year),
        school_type=None,
        discovery_evidence_path=Path("output") / "discovery_rejections.jsonl",
    )


def validate_operator_settings(
    *,
    fiscal_era_enabled: bool,
    fiscal_era_name: str,
    fiscal_era_romanized: str,
    fiscal_era_initial: str,
) -> list[str]:
    errors: list[str] = []
    if fiscal_era_enabled:
        if not fiscal_era_name.strip():
            errors.append("和暦名を入力してください。")
        if not _clean_romanized(fiscal_era_romanized):
            errors.append("検索用 romanized を英数字で入力してください。")
        if not _clean_romanized(fiscal_era_initial):
            errors.append("検索用 initial を英数字で入力してください。")
    return errors


def read_build_info(app_root: Path) -> dict[str, str]:
    """Read optional build metadata for operator version checks."""
    path = app_root / "BUILD_INFO.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, str] = {}
    for key in BUILD_INFO_DISPLAY_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            out[key] = value
    return out


def build_info_summary(build_info: dict[str, str]) -> str:
    """Return a compact build label safe for Streamlit captions."""
    commit = build_info.get("git_commit", "")
    commit_label = commit[:7] if len(commit) >= 7 else commit or "unknown"
    branch = build_info.get("git_branch") or "unknown"
    dirty = build_info.get("git_dirty") or "unknown"
    built_at = build_info.get("built_at_utc") or "unknown"
    return f"commit={commit_label} / branch={branch} / dirty={dirty} / built={built_at}"


def _provider_index(provider: str) -> int:
    providers = ["duckduckgo", "serper", "brave", "google", "external"]
    return providers.index(provider) if provider in providers else 0


def _ocr_mode_index(value: str) -> int:
    modes = ["auto", "on", "off"]
    return modes.index(value) if value in modes else 0


def _url_search_mode_index(value: str) -> int:
    modes = ["auto", "on", "off"]
    return modes.index(value) if value in modes else 0


def render(_session: object, *, lock_path: Path) -> None:
    """Top-level Streamlit render for the settings page."""
    session = _session if isinstance(_session, Session) else None
    st.header("設定")
    st.caption(
        "対象年度と、政府・学校ページで使われる和暦検索名を確認します。"
        "年度の中身は西暦で保持し、和暦は表示と検索だけに使います。"
    )

    env_path = Path(settings.app_root) / ".env"
    st.info(f"保存先: {env_path}")

    build_info = read_build_info(Path(settings.app_root))
    if build_info:
        st.subheader("バージョン")
        st.caption(build_info_summary(build_info))

    old_target_fiscal_year = int(settings.target_fiscal_year)
    lock_status = probe_lock(lock_path)
    if lock_status.held:
        st.warning(
            "初回取得または週次処理中のため、設定保存は一時停止しています。"
            "処理完了後にもう一度保存してください。"
        )

    target_fiscal_year = int(
        st.number_input(
            "対象年度（西暦）",
            min_value=MIN_SUPPORTED_TARGET_FISCAL_YEAR,
            max_value=MAX_SUPPORTED_TARGET_FISCAL_YEAR,
            value=int(settings.target_fiscal_year),
            step=1,
        )
    )

    st.subheader("和暦 alias")
    fiscal_era_enabled = st.checkbox("和暦を表示・検索に使う", value=bool(settings.fiscal_era_enabled))
    fiscal_era_name = st.text_input("和暦名", value=str(settings.fiscal_era_name), disabled=not fiscal_era_enabled)
    fiscal_era_start_year = int(
        st.number_input(
            "この和暦の1年度目（公历）",
            min_value=1800,
            max_value=2100,
            value=int(settings.fiscal_era_start_year),
            step=1,
            disabled=not fiscal_era_enabled,
        )
    )
    col1, col2 = st.columns(2)
    with col1:
        fiscal_era_romanized = st.text_input(
            "検索用 romanized",
            value=str(settings.fiscal_era_romanized),
            disabled=not fiscal_era_enabled,
        )
    with col2:
        fiscal_era_initial = st.text_input(
            "検索用 initial",
            value=str(settings.fiscal_era_initial),
            max_chars=1,
            disabled=not fiscal_era_enabled,
        )

    preview_eras: tuple[JapaneseEra, ...] = ()
    if fiscal_era_enabled and fiscal_era_name.strip():
        preview_eras = (
            JapaneseEra(
                name=fiscal_era_name.strip(),
                romanized=_clean_romanized(fiscal_era_romanized),
                initial=_clean_romanized(fiscal_era_initial)[:1],
                start_fiscal_year=fiscal_era_start_year,
            ),
        )
    st.metric("保存後の表示", format_fiscal_year_label(target_fiscal_year, eras=preview_eras))
    st.caption(f"現在の表示: {format_fiscal_year_label(settings.target_fiscal_year)}")

    st.subheader("OCR")
    ocr_auto_enable = st.selectbox(
        "OCR 自動処理",
        ["auto", "on", "off"],
        index=_ocr_mode_index(str(settings.ocr_auto_enable)),
        format_func=lambda value: {
            "auto": "自動判定",
            "on": "常に使う",
            "off": "使わない",
        }[value],
    )
    ocr_col1, ocr_col2 = st.columns(2)
    with ocr_col1:
        ocr_min_cpus = int(
            st.number_input(
                "OCR 最小 CPU 数",
                min_value=1,
                max_value=64,
                value=int(settings.ocr_min_cpus),
                step=1,
            )
        )
    with ocr_col2:
        ocr_min_free_ram_mb = int(
            st.number_input(
                "OCR 最小空きメモリ MB",
                min_value=512,
                max_value=262144,
                value=int(settings.ocr_min_free_ram_mb),
                step=512,
            )
        )
    tesseract_bin = st.text_input("Tesseract path", value=str(settings.tesseract_bin))
    ocr_provider = st.text_input("OCR provider", value=str(settings.ocr_provider))
    ocr_device = st.text_input("OCR device", value=str(settings.ocr_device))

    st.subheader("外部 API")
    search_provider = st.selectbox(
        "学校URL検索 provider",
        ["duckduckgo", "serper", "brave", "google", "external"],
        index=_provider_index(str(settings.search_provider)),
        format_func=lambda value: {
            "duckduckgo": "DuckDuckGo（API key なし）",
            "serper": "Serper",
            "brave": "Brave Search",
            "google": "Google Custom Search",
            "external": "External command（環境変数のみ）",
        }[value],
    )
    if search_provider == "external":
        st.info(
            "External command provider は EIDP_EXTERNAL_SEARCH_COMMAND で管理します。"
            "ここでは任意コマンドを保存しません。"
        )
    url_search_auto_enable = st.selectbox(
        "不足URLのWeb検索補完",
        ["auto", "on", "off"],
        index=_url_search_mode_index(str(settings.url_search_auto_enable)),
        format_func=lambda value: {
            "auto": "自動（設定済み provider で実行）",
            "on": "常に実行",
            "off": "実行しない",
        }[value],
    )
    url_search_batch_size = int(
        st.number_input(
            "Web検索補完の最大校数",
            min_value=0,
            max_value=5000,
            value=int(settings.url_search_batch_size),
            step=50,
            disabled=url_search_auto_enable == "off",
        )
    )
    api_col1, api_col2 = st.columns(2)
    with api_col1:
        serper_api_key = st.text_input("Serper API key", value=str(settings.serper_api_key), type="password")
        brave_api_key = st.text_input("Brave API key", value=str(settings.brave_api_key), type="password")
    with api_col2:
        google_api_key = st.text_input("Google API key", value=str(settings.google_api_key), type="password")
        google_cx = st.text_input("Google CX", value=str(settings.google_cx), type="password")
    firecrawl_api_key = st.text_input(
        "Firecrawl API key",
        value=str(settings.firecrawl_api_key),
        type="password",
    )

    errors = validate_operator_settings(
        fiscal_era_enabled=fiscal_era_enabled,
        fiscal_era_name=fiscal_era_name,
        fiscal_era_romanized=fiscal_era_romanized,
        fiscal_era_initial=fiscal_era_initial,
    )
    for error in errors:
        st.error(error)

    if st.button("設定を保存", type="primary", disabled=bool(errors) or lock_status.held):
        if session is None:
            st.error("DB セッションが取得できません。アプリを再起動してから保存してください。")
            return
        try:
            with acquire_lock(lock_path, owner="ui_settings"):
                updates = save_operator_settings(
                    env_path,
                    target_fiscal_year=target_fiscal_year,
                    fiscal_era_enabled=fiscal_era_enabled,
                    fiscal_era_name=fiscal_era_name,
                    fiscal_era_romanized=fiscal_era_romanized,
                    fiscal_era_initial=fiscal_era_initial,
                    fiscal_era_start_year=fiscal_era_start_year,
                    ocr_auto_enable=ocr_auto_enable,
                    ocr_min_cpus=ocr_min_cpus,
                    ocr_min_free_ram_mb=ocr_min_free_ram_mb,
                    tesseract_bin=tesseract_bin,
                    ocr_provider=ocr_provider,
                    ocr_device=ocr_device,
                    search_provider=search_provider,
                    url_search_auto_enable=url_search_auto_enable,
                    url_search_batch_size=url_search_batch_size,
                    serper_api_key=serper_api_key,
                    brave_api_key=brave_api_key,
                    google_api_key=google_api_key,
                    google_cx=google_cx,
                    firecrawl_api_key=firecrawl_api_key,
                )
                rebuild_stats = maybe_rebuild_school_year_tasks_after_target_change(
                    session,
                    old_target_fiscal_year=old_target_fiscal_year,
                    target_fiscal_year=target_fiscal_year,
                )
                audit_operator_settings_saved(
                    session,
                    old_target_fiscal_year=old_target_fiscal_year,
                    target_fiscal_year=target_fiscal_year,
                    updates=updates,
                    rebuild_stats=rebuild_stats,
                )
                session.commit()
        except LockBusyError:
            session.rollback()
            st.error("別の処理が実行中です。完了後にもう一度保存してください。")
            return
        except Exception:
            session.rollback()
            raise

        if rebuild_stats is not None:
            st.success(
                "保存しました。対象年度が変わったため、年度タスクも再計算しました。"
                f"対象校 {rebuild_stats.rebuilt} 校 / Excel出力可 {rebuild_stats.excel_ready} 校"
            )
        else:
            st.success("保存しました。この画面を再読み込みするとサイドバーにも反映されます。")
