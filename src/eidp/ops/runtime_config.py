"""Strict, non-executable parsing for the Linux Web runtime configuration."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

_ALLOWED_KEYS = frozenset(
    {
        "EIDP_WEB_PORT",
        "EIDP_WEB_BASE_URL_PATH",
        "EIDP_INTERNAL_BASE_URL",
        "EIDP_WEB_MAX_UPLOAD_MB",
    }
)
_ASSIGNMENT_PATTERN = re.compile(r"(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*)")
_BASE_PATH_SEGMENT_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]*")
_SHELL_METACHARACTERS = frozenset("$`'\"\\;|&<>")


@dataclass(frozen=True)
class RuntimeLaunchConfig:
    """Validated values passed to a Streamlit child process."""

    port: int = 8502
    base_url_path: str = ""
    internal_base_url: str = ""
    max_upload_mb: int = 200

    def as_streamlit_env(self) -> dict[str, str]:
        values = {
            "STREAMLIT_SERVER_PORT": str(self.port),
            "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": str(self.max_upload_mb),
            "STREAMLIT_SERVER_BASE_URL_PATH": self.base_url_path.lstrip("/"),
        }
        if self.internal_base_url:
            public = urlsplit(self.internal_base_url)
            origin = f"{public.scheme}://{public.netloc}"
            values["STREAMLIT_BROWSER_SERVER_ADDRESS"] = public.hostname or ""
            values["STREAMLIT_BROWSER_SERVER_PORT"] = str(
                public.port or (443 if public.scheme == "https" else 80)
            )
            values["STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS"] = json.dumps([origin])
        return values


def load_runtime_config(path: Path) -> RuntimeLaunchConfig:
    """Read and validate the allowlisted runtime settings in ``path``."""

    values = _parse_allowed_assignments(path)
    config = RuntimeLaunchConfig(
        port=_validated_port(values.get("EIDP_WEB_PORT", "8502")),
        base_url_path=_validated_base_path(values.get("EIDP_WEB_BASE_URL_PATH", "")),
        internal_base_url=_validated_http_url(values.get("EIDP_INTERNAL_BASE_URL", "")),
        max_upload_mb=_validated_positive_int(values.get("EIDP_WEB_MAX_UPLOAD_MB", "200")),
    )
    _require_public_url_path_match(config)
    return config


def sanitized_child_env(inherited: Mapping[str, str], config: RuntimeLaunchConfig) -> dict[str, str]:
    """Return inherited environment data with runtime overrides removed."""

    blocked_prefixes = ("STREAMLIT_SERVER_", "STREAMLIT_BROWSER_")
    child = {
        key: value
        for key, value in inherited.items()
        if key != "EIDP_WEB_PORT" and not key.startswith(blocked_prefixes)
    }
    child.update(config.as_streamlit_env())
    return child


def _parse_allowed_assignments(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    body = path.read_text(encoding="utf-8")
    if any(_is_disallowed_control_character(character) for character in body):
        raise ValueError("runtime configuration contains a control character")

    values: dict[str, str] = {}
    for line_number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = _ASSIGNMENT_PATTERN.fullmatch(line)
        if match is None:
            raise ValueError(f"runtime configuration line {line_number} is not a literal KEY=value assignment")

        key = match.group("key")
        if key not in _ALLOWED_KEYS:
            continue
        if key in values:
            raise ValueError(f"duplicate runtime configuration key: {key}")

        value = match.group("value")
        _require_literal_value(key, value)
        values[key] = value

    return values


def _is_disallowed_control_character(character: str) -> bool:
    return character not in {"\n", "\r"} and unicodedata.category(character) == "Cc"


def _require_literal_value(key: str, value: str) -> None:
    if value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{key} must be a literal value without whitespace")
    if any(character in _SHELL_METACHARACTERS for character in value):
        raise ValueError(f"{key} must not contain shell syntax")


def _validated_port(value: str) -> int:
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError("EIDP_WEB_PORT must be an integer port")
    port = int(value)
    if not 1 <= port <= 65535:
        raise ValueError("EIDP_WEB_PORT port must be between 1 and 65535")
    return port


def _validated_positive_int(value: str) -> int:
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError("EIDP_WEB_MAX_UPLOAD_MB must be a positive integer")
    number = int(value)
    if number <= 0:
        raise ValueError("EIDP_WEB_MAX_UPLOAD_MB must be a positive integer")
    return number


def _validated_base_path(value: str) -> str:
    if value in {"", "/"}:
        return ""
    if not value.startswith("/") or value.startswith("//"):
        raise ValueError("EIDP_WEB_BASE_URL_PATH must be empty or an absolute base URL path")

    normalized = value[:-1] if value.endswith("/") else value
    segments = normalized[1:].split("/")
    if any(
        segment in {"", ".", ".."} or _BASE_PATH_SEGMENT_PATTERN.fullmatch(segment) is None
        for segment in segments
    ):
        raise ValueError("EIDP_WEB_BASE_URL_PATH contains an invalid base URL path segment")
    return normalized


def _validated_http_url(value: str) -> str:
    if not value:
        return ""
    if any(character.isspace() for character in value):
        raise ValueError("EIDP_INTERNAL_BASE_URL must be an absolute HTTP URL")

    try:
        public = urlsplit(value)
        port = public.port
    except ValueError as exc:
        raise ValueError("EIDP_INTERNAL_BASE_URL is not a valid internal base URL") from exc

    if public.scheme not in {"http", "https"} or not public.netloc or not public.hostname:
        raise ValueError("EIDP_INTERNAL_BASE_URL must be an absolute HTTP URL")
    if public.username is not None or public.password is not None:
        raise ValueError("EIDP_INTERNAL_BASE_URL internal base URL must not contain userinfo")
    if "?" in value or "#" in value:
        raise ValueError("EIDP_INTERNAL_BASE_URL internal base URL must not contain a query or fragment")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("EIDP_INTERNAL_BASE_URL internal base URL has an invalid port")
    return value


def _require_public_url_path_match(config: RuntimeLaunchConfig) -> None:
    if not config.internal_base_url:
        return

    public_path = _validated_base_path(urlsplit(config.internal_base_url).path)
    if public_path != config.base_url_path:
        raise ValueError("EIDP_INTERNAL_BASE_URL path must match EIDP_WEB_BASE_URL_PATH")
