"""Sprint 8.5.a.2 — assemble the Windows runtime that the operator ZIP needs.

The Windows operator PC has no preinstalled Python. ``first_setup.bat``
expects:

    %EIDP_APP_ROOT%\\runtime\\python\\python.exe
    %EIDP_APP_ROOT%\\runtime\\uv.exe

This script populates that ``runtime/`` directory by downloading:

* `python-build-standalone <https://github.com/astral-sh/python-build-standalone>`_
  — the ``cpython-3.12.x-x86_64-pc-windows-msvc-install_only.tar.gz``
  archive, which already lays out as ``python/python.exe + python/Lib + ...``.
* `uv.exe <https://github.com/astral-sh/uv>`_ — the standalone installer
  pulled from the official ``uv-x86_64-pc-windows-msvc.zip`` archive.

What we promise on Mac side
---------------------------
We can verify file shape (the archive contains ``python/python.exe`` /
``uv.exe``) and SHA-256 checksums. We do NOT execute the binaries; that
is reserved for the Windows VM offline validation gate (Sprint 8.5.b).

What we do not do
-----------------
* Auto-resolve the latest python-build-standalone release. The release
  tag and SHA-256 are pinned in this script so a future ZIP rebuild is
  byte-reproducible. Bumping the runtime is a one-line change reviewed
  in PR.
* Install onto the Mac. The Windows binaries live under ``runtime/`` of
  the operator install, never on the dev host.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "runtime"

# Sentinel returned by ``verify_sha256`` if a constants table still
# carries the placeholder. Tests check production constants do NOT
# carry this sentinel.
PIN_SENTINEL = "PINNED_AFTER_FIRST_DOWNLOAD"

# Pin to a verified python-build-standalone release. cp312, install_only
# layout (the archive lays out as ``python/python.exe + python/Lib + ...``).
# Bump release_tag + sha256 atomically when upgrading; sha256 must come
# from the upstream SHA256SUMS file in the same release. Note the URL
# uses ``%2B`` for the ``+`` between version and date because the
# browser_download_url returned by the GitHub API URL-encodes it.
PYTHON_BUILD_STANDALONE = {
    "release_tag": "20260414",
    "filename": "cpython-3.12.13+20260414-x86_64-pc-windows-msvc-install_only.tar.gz",
    "url": (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        "20260414/cpython-3.12.13%2B20260414-x86_64-pc-windows-msvc-install_only.tar.gz"
    ),
    "sha256": "c5a9e011e284c49c48106ca177342f3e3f64e95b4c6652d4a382cc7c9bb1cc46",
}

# Pin uv release. SHA-256 lifted verbatim from the official
# ``uv-x86_64-pc-windows-msvc.zip.sha256`` sidecar in the same release.
UV_WINDOWS = {
    "release_tag": "0.11.8",
    "filename": "uv-x86_64-pc-windows-msvc.zip",
    "url": "https://github.com/astral-sh/uv/releases/download/0.11.8/uv-x86_64-pc-windows-msvc.zip",
    "sha256": "c84629a56e0706b69a47ea35862208af827cb6fbfa1d0ca763c52c67594637e8",
}


class RuntimeAssetError(RuntimeError):
    """Raised when a download or verification step fails."""


@dataclass
class RuntimeManifest:
    python_archive: Path
    uv_archive: Path
    python_dir: Path
    uv_exe: Path


# ---------------------------------------------------------------------------
# Download + checksum
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_to(url: str, dest: Path, *, opener=urllib.request.urlopen) -> Path:
    """Download ``url`` to ``dest``. Returns ``dest``. ``opener`` is an
    injection seam for tests."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"-> {url}\n   into {dest}")
    with opener(url) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    return dest


def verify_sha256(path: Path, expected: str) -> None:
    """Raise if file SHA-256 does not match ``expected``.

    Special-case sentinel ``PINNED_AFTER_FIRST_DOWNLOAD`` — it means the
    pin has not been recorded yet. We compute and print the actual
    digest so the operator can update the script and re-run with a real
    pin in place. Treated as a hard failure so we don't ship an
    unverified runtime.
    """
    actual = sha256_file(path)
    if expected == PIN_SENTINEL:
        raise RuntimeAssetError(
            f"checksum pin missing for {path.name}; record sha256={actual}"
        )
    if actual != expected:
        raise RuntimeAssetError(
            f"checksum mismatch for {path.name}: expected={expected} actual={actual}"
        )


# ---------------------------------------------------------------------------
# Archive shape verification + extract
# ---------------------------------------------------------------------------


def verify_python_archive_shape(archive: Path) -> None:
    """Confirm the python-build-standalone tarball lays out as
    ``python/python.exe`` so first_setup.bat finds the binary at the
    expected path. We only inspect the archive listing — no extraction
    required for the shape check.

    The ``install_only`` flavor lays the binary at ``python/python.exe``
    and that is the only path we accept. Earlier scaffolding allowed a
    speculative ``python/install/python.exe`` fallback; we drop that
    because (a) the install_only flavor never produces it and (b) if we
    accepted it we would break ``first_setup.bat`` which expects
    ``runtime/python/python.exe`` after extraction.
    """
    if not tarfile.is_tarfile(archive):
        raise RuntimeAssetError(f"not a tar archive: {archive}")
    with tarfile.open(archive, "r:*") as tf:
        names = set(tf.getnames())
    if "python/python.exe" not in names:
        raise RuntimeAssetError(
            f"python-build-standalone archive missing python/python.exe at top level: "
            f"sample names={sorted(list(names))[:5]}"
        )


def verify_uv_archive_shape(archive: Path) -> None:
    """Confirm the uv zip ships ``uv.exe`` at the top level."""
    if not zipfile.is_zipfile(archive):
        raise RuntimeAssetError(f"not a zip archive: {archive}")
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    if "uv.exe" not in names and "uv-x86_64-pc-windows-msvc/uv.exe" not in names:
        raise RuntimeAssetError(
            f"uv archive missing uv.exe at top level or under release dir: "
            f"sample names={sorted(list(names))[:5]}"
        )


def extract_python_archive(archive: Path, dest_runtime: Path) -> Path:
    """Extract ``cpython-...tar.gz`` into ``dest_runtime / python``."""
    target = dest_runtime / "python"
    if target.exists():
        return target
    dest_runtime.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:*") as tf:
        # The archive's top folder is already named ``python`` so we
        # extract directly into dest_runtime.
        tf.extractall(dest_runtime, filter="data")
    if not target.is_dir():
        raise RuntimeAssetError(f"expected {target} after extraction; got {list(dest_runtime.iterdir())}")
    return target


def extract_uv_archive(archive: Path, dest_runtime: Path) -> Path:
    """Place ``uv.exe`` directly under ``dest_runtime``."""
    target = dest_runtime / "uv.exe"
    if target.exists():
        return target
    dest_runtime.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        candidates = [n for n in zf.namelist() if n.endswith("uv.exe")]
        if not candidates:
            raise RuntimeAssetError(f"uv archive contains no uv.exe: {zf.namelist()}")
        # Always pick the shortest name so we get the top-level entry.
        member = min(candidates, key=len)
        with zf.open(member) as src, target.open("wb") as out:
            out.write(src.read())
    return target


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def download_and_extract_runtime(
    *,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    cache_dir: Path | None = None,
    opener=urllib.request.urlopen,
) -> RuntimeManifest:
    """End-to-end download + verify + extract.

    ``cache_dir`` lets repeated builds reuse already-downloaded
    archives; defaults to ``runtime_dir.parent / .runtime-cache``.
    ``opener`` is an injection seam for tests so we never hit the live
    network during unit tests.
    """
    if cache_dir is None:
        cache_dir = runtime_dir.parent / ".runtime-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    py_archive = cache_dir / PYTHON_BUILD_STANDALONE["filename"]
    uv_archive = cache_dir / UV_WINDOWS["filename"]

    if not py_archive.exists():
        download_to(PYTHON_BUILD_STANDALONE["url"], py_archive, opener=opener)
    verify_sha256(py_archive, PYTHON_BUILD_STANDALONE["sha256"])
    verify_python_archive_shape(py_archive)

    if not uv_archive.exists():
        download_to(UV_WINDOWS["url"], uv_archive, opener=opener)
    verify_sha256(uv_archive, UV_WINDOWS["sha256"])
    verify_uv_archive_shape(uv_archive)

    python_dir = extract_python_archive(py_archive, runtime_dir)
    uv_exe = extract_uv_archive(uv_archive, runtime_dir)

    return RuntimeManifest(
        python_archive=py_archive,
        uv_archive=uv_archive,
        python_dir=python_dir,
        uv_exe=uv_exe,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the Windows runtime for the operator ZIP.")
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        manifest = download_and_extract_runtime(
            runtime_dir=args.runtime_dir,
            cache_dir=args.cache_dir,
        )
    except RuntimeAssetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"OK: python at {manifest.python_dir}")
    print(f"OK: uv at {manifest.uv_exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
