from __future__ import annotations

from pathlib import Path

import pytest

from eidp.ops.runtime_config import RuntimeLaunchConfig, load_runtime_config, sanitized_child_env


def _write_env(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_runtime_config_uses_safe_defaults_for_an_empty_file(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / ".env", "\n# No runtime overrides.\n")

    config = load_runtime_config(env_file)

    assert config == RuntimeLaunchConfig()
    assert config.as_streamlit_env() == {
        "STREAMLIT_SERVER_PORT": "8502",
        "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": "200",
        "STREAMLIT_SERVER_BASE_URL_PATH": "",
    }


def test_runtime_config_accepts_all_four_allowed_keys(tmp_path: Path) -> None:
    env_file = _write_env(
        tmp_path / ".env",
        "\n".join(
            (
                "EIDP_WEB_PORT=8600",
                "EIDP_WEB_BASE_URL_PATH=/eidp/",
                "EIDP_INTERNAL_BASE_URL=https://eidp.internal.example:9443/eidp/",
                "EIDP_WEB_MAX_UPLOAD_MB=512",
                "",
            )
        ),
    )

    config = load_runtime_config(env_file)

    assert config == RuntimeLaunchConfig(
        port=8600,
        base_url_path="/eidp",
        internal_base_url="https://eidp.internal.example:9443/eidp/",
        max_upload_mb=512,
    )
    assert config.as_streamlit_env() == {
        "STREAMLIT_SERVER_PORT": "8600",
        "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": "512",
        "STREAMLIT_SERVER_BASE_URL_PATH": "eidp",
        "STREAMLIT_BROWSER_SERVER_ADDRESS": "eidp.internal.example",
        "STREAMLIT_BROWSER_SERVER_PORT": "9443",
        "STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS": '["https://eidp.internal.example:9443"]',
    }


def test_runtime_config_does_not_execute_or_accept_unknown_keys(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"EIDP_WEB_PORT=8502\nEIDP_PROXY_SHARED_SECRET=$(touch {marker})\n",
        encoding="utf-8",
    )

    config = load_runtime_config(env_file)

    assert config.port == 8502
    assert not marker.exists()
    assert "EIDP_PROXY_SHARED_SECRET" not in config.as_streamlit_env()


def test_runtime_config_rejects_duplicate_allowed_keys(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / ".env", "EIDP_WEB_PORT=8502\nEIDP_WEB_PORT=8503\n")

    with pytest.raises(ValueError, match="duplicate"):
        load_runtime_config(env_file)


def test_runtime_config_rejects_malformed_assignments(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / ".env", "EIDP_WEB_PORT 8502\n")

    with pytest.raises(ValueError, match="assignment"):
        load_runtime_config(env_file)


@pytest.mark.parametrize("control_character", ("\x00", "\x80", "\x9f"))
def test_runtime_config_rejects_control_characters(tmp_path: Path, control_character: str) -> None:
    env_file = _write_env(
        tmp_path / ".env",
        f"EIDP_INTERNAL_BASE_URL=https://eidp.internal.example{control_character}\n",
    )

    with pytest.raises(ValueError, match="control"):
        load_runtime_config(env_file)


@pytest.mark.parametrize(
    "assignment",
    (
        "EIDP_WEB_PORT=$(printf 8502)",
        "EIDP_WEB_PORT=`printf 8502`",
        "export EIDP_WEB_PORT=8502",
    ),
)
def test_runtime_config_rejects_shell_syntax(tmp_path: Path, assignment: str) -> None:
    env_file = _write_env(tmp_path / ".env", f"{assignment}\n")

    with pytest.raises(ValueError):
        load_runtime_config(env_file)


@pytest.mark.parametrize("port", ("0", "65536", "not-a-port"))
def test_runtime_config_rejects_invalid_ports(tmp_path: Path, port: str) -> None:
    env_file = _write_env(tmp_path / ".env", f"EIDP_WEB_PORT={port}\n")

    with pytest.raises(ValueError, match="port"):
        load_runtime_config(env_file)


@pytest.mark.parametrize("base_path", ("/../eidp", "/eidp?debug=1", "/eidp//admin"))
def test_runtime_config_rejects_invalid_base_paths(tmp_path: Path, base_path: str) -> None:
    env_file = _write_env(tmp_path / ".env", f"EIDP_WEB_BASE_URL_PATH={base_path}\n")

    with pytest.raises(ValueError, match="base URL path"):
        load_runtime_config(env_file)


def test_runtime_config_rejects_non_http_urls(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / ".env", "EIDP_INTERNAL_BASE_URL=ftp://eidp.internal.example\n")

    with pytest.raises(ValueError, match="HTTP"):
        load_runtime_config(env_file)


@pytest.mark.parametrize("max_upload_mb", ("0", "-1"))
def test_runtime_config_rejects_non_positive_upload_size(tmp_path: Path, max_upload_mb: str) -> None:
    env_file = _write_env(tmp_path / ".env", f"EIDP_WEB_MAX_UPLOAD_MB={max_upload_mb}\n")

    with pytest.raises(ValueError, match="positive"):
        load_runtime_config(env_file)


@pytest.mark.parametrize(
    "url",
    (
        "https://operator:secret@eidp.internal.example",
        "https://eidp.internal.example?debug=1",
        "https://eidp.internal.example?",
        "https://eidp.internal.example#status",
        "https://eidp.internal.example#",
    ),
)
def test_runtime_config_rejects_url_userinfo_query_and_fragment(tmp_path: Path, url: str) -> None:
    env_file = _write_env(tmp_path / ".env", f"EIDP_INTERNAL_BASE_URL={url}\n")

    with pytest.raises(ValueError, match="internal base URL"):
        load_runtime_config(env_file)


def test_runtime_config_requires_public_url_path_to_match_normalized_base_path(tmp_path: Path) -> None:
    matching = _write_env(
        tmp_path / "matching.env",
        "EIDP_WEB_BASE_URL_PATH=/eidp/\nEIDP_INTERNAL_BASE_URL=https://eidp.internal.example/eidp/\n",
    )
    mismatching = _write_env(
        tmp_path / "mismatching.env",
        "EIDP_WEB_BASE_URL_PATH=/eidp\nEIDP_INTERNAL_BASE_URL=https://eidp.internal.example/other\n",
    )

    assert load_runtime_config(matching).base_url_path == "/eidp"
    with pytest.raises(ValueError, match="path"):
        load_runtime_config(mismatching)


def test_runtime_config_requires_empty_base_path_for_root_url(tmp_path: Path) -> None:
    root = _write_env(tmp_path / "root.env", "EIDP_INTERNAL_BASE_URL=https://eidp.internal.example/\n")
    mismatching = _write_env(
        tmp_path / "mismatching.env",
        "EIDP_WEB_BASE_URL_PATH=/eidp\nEIDP_INTERNAL_BASE_URL=https://eidp.internal.example/\n",
    )

    assert load_runtime_config(root).base_url_path == ""
    with pytest.raises(ValueError, match="path"):
        load_runtime_config(mismatching)


def test_sanitized_child_env_blocks_inherited_runtime_overrides() -> None:
    inherited = {
        "EIDP_WEB_PORT": "9999",
        "STREAMLIT_SERVER_PORT": "9999",
        "STREAMLIT_SERVER_ADDRESS": "0.0.0.0",
        "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": "9999",
        "STREAMLIT_SERVER_BASE_URL_PATH": "untrusted",
        "STREAMLIT_SERVER_CUSTOM_OPTION": "untrusted",
        "STREAMLIT_BROWSER_SERVER_ADDRESS": "untrusted.example",
        "STREAMLIT_BROWSER_SERVER_PORT": "9999",
        "STREAMLIT_BROWSER_CUSTOM_OPTION": "untrusted",
        "EIDP_APP_ROOT": "/home/junming/EIDP",
    }
    config = RuntimeLaunchConfig(
        port=8600,
        base_url_path="/eidp",
        internal_base_url="https://eidp.internal.example/eidp",
        max_upload_mb=512,
    )

    child = sanitized_child_env(inherited, config)

    assert child == {
        "EIDP_APP_ROOT": "/home/junming/EIDP",
        "STREAMLIT_SERVER_PORT": "8600",
        "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": "512",
        "STREAMLIT_SERVER_BASE_URL_PATH": "eidp",
        "STREAMLIT_BROWSER_SERVER_ADDRESS": "eidp.internal.example",
        "STREAMLIT_BROWSER_SERVER_PORT": "443",
        "STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS": '["https://eidp.internal.example"]',
    }


def test_linux_env_template_exposes_only_validated_runtime_settings() -> None:
    body = Path("deploy/linux/env.example").read_text(encoding="utf-8")
    active_lines = {
        line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")
    }

    assert "EIDP_WEB_PORT=8502" in active_lines
    assert "EIDP_WEB_BASE_URL_PATH=" in active_lines
    assert "EIDP_INTERNAL_BASE_URL=" in active_lines
    assert "EIDP_WEB_MAX_UPLOAD_MB=200" in active_lines
    assert not any(line.startswith("EIDP_WEB_BIND=") for line in active_lines)
