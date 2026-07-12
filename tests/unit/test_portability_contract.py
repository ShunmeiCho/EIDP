from __future__ import annotations

import getpass
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {".cfg", ".ini", ".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml"}
GENERIC_USERS = {"", "root", "runner", "vscode", "codespace"}
MAC_REAL_USER_PATH_RE = re.compile(r"/Users/(?!<user>(?:/|$))[^/\s`\"'<>]+")


def _local_user_tokens() -> tuple[str, ...]:
    users = {getpass.getuser(), Path.home().name}
    users.update(
        user.strip()
        for user in os.environ.get("EIDP_FORBIDDEN_LOCAL_USERS", "").split(",")
        if user.strip()
    )
    tokens: list[str] = []
    for user in sorted(users - GENERIC_USERS):
        tokens.extend(
            [
                user,
                f"/Users/{user}",
            ]
        )
    return tuple(tokens)


def _iter_checked_files() -> list[Path]:
    roots = [
        REPO_ROOT / "tests",
        REPO_ROOT / "scripts",
        REPO_ROOT / "src",
        REPO_ROOT / ".github",
    ]
    files: list[Path] = [REPO_ROOT / "pyproject.toml"]
    for root in roots:
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
        )
    files.extend(
        [
            REPO_ROOT / "docs" / "runbooks" / "linux-web-dev-run.md",
            REPO_ROOT / "deploy" / "linux" / "server-requirements.md",
        ]
    )
    return sorted(set(files))


def test_runtime_tests_ci_and_packaged_operator_docs_do_not_hardcode_local_usernames() -> None:
    offenders: list[str] = []
    for path in _iter_checked_files():
        body = path.read_text(encoding="utf-8", errors="ignore")
        for token in _local_user_tokens():
            if token in body:
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}: contains {token!r}")

    assert offenders == []


def test_linux_deployment_docs_do_not_embed_local_macos_home_paths() -> None:
    offenders: list[str] = []
    for path in [
        REPO_ROOT / "docs" / "runbooks" / "linux-web-dev-run.md",
        REPO_ROOT / "deploy" / "linux" / "server-requirements.md",
    ]:
        body = path.read_text(encoding="utf-8", errors="ignore")
        if MAC_REAL_USER_PATH_RE.search(body):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []
