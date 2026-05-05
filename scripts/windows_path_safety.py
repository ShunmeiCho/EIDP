"""Shared Windows path-safety checks for repository paths and ZIP entries."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")


@dataclass(frozen=True)
class WindowsPathIssue:
    kind: str
    path: str
    detail: str


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _path_parts(path: str) -> list[str]:
    return [part for part in normalize_path(path).strip("/").split("/") if part]


def _reserved_basename(component: str) -> str:
    # Windows ignores trailing dots/spaces and reserves device names even
    # when an extension is present, e.g. CON.txt.
    clean = component.rstrip(" .")
    return clean.split(".", 1)[0].upper()


def check_windows_safe_paths(paths: Iterable[str]) -> list[WindowsPathIssue]:
    issues: list[WindowsPathIssue] = []
    seen: dict[str, str] = {}

    for original in sorted({str(path) for path in paths}):
        normalized = normalize_path(original)
        if not normalized:
            continue

        if normalized.startswith("/") or _WINDOWS_DRIVE_RE.match(normalized):
            issues.append(
                WindowsPathIssue(
                    "absolute-path",
                    original,
                    "absolute paths are unsafe in ZIP/repo manifests",
                )
            )

        parts = _path_parts(normalized)
        if any(part == ".." for part in parts):
            issues.append(WindowsPathIssue("parent-directory", original, "parent-directory components are unsafe"))

        clean_for_collision = PurePosixPath(*parts).as_posix() if parts else normalized.strip("/")
        collision_key = clean_for_collision.casefold()
        previous = seen.setdefault(collision_key, original)
        if previous != original:
            issues.append(
                WindowsPathIssue(
                    "case-collision",
                    original,
                    f"collides with {previous} on a case-insensitive filesystem",
                )
            )

        for part in parts:
            if part.endswith((" ", ".")):
                issues.append(
                    WindowsPathIssue(
                        "trailing-dot-space",
                        original,
                        f"path component {part!r} ends with a dot or space, which Windows normalizes",
                    )
                )
                break

            if _reserved_basename(part) in WINDOWS_RESERVED_BASENAMES:
                issues.append(
                    WindowsPathIssue(
                        "reserved-name",
                        original,
                        f"path component {part!r} is a reserved Windows device name",
                    )
                )
                break

    return issues


def issues_by_kind(issues: Iterable[WindowsPathIssue]) -> dict[str, list[WindowsPathIssue]]:
    grouped: dict[str, list[WindowsPathIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.kind, []).append(issue)
    return grouped


def render_issues(issues: Iterable[WindowsPathIssue]) -> str:
    rows = list(issues)
    if not rows:
        return "OK: all paths are Windows-safe"
    lines = ["FAIL: Windows-unsafe paths detected"]
    for issue in rows:
        lines.append(f"  {issue.kind}: {issue.path} ({issue.detail})")
    return "\n".join(lines)
