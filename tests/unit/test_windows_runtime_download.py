"""Sprint 8.5.a.2 — Windows runtime download script.

Mac-side guards: SHA-256 verification, archive shape, extraction layout,
and integration with build_windows_zip.py. We never hit the network in
unit tests; downloads are stubbed via the ``opener`` injection seam.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_runtime_script():
    spec = importlib.util.spec_from_file_location(
        "download_windows_runtime", SCRIPTS_DIR / "download_windows_runtime.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_build_script():
    spec = importlib.util.spec_from_file_location(
        "build_windows_zip", SCRIPTS_DIR / "build_windows_zip.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixture builders — produce realistic-shaped fake archives in tmp_path
# ---------------------------------------------------------------------------


def _make_fake_python_archive(path: Path, *, content: bytes = b"MZ\x90\x00FAKE_PYTHON") -> str:
    """Build a tar.gz archive that mirrors python-build-standalone's
    ``install_only`` layout and return its sha256."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in [
            ("python/python.exe", content),
            ("python/Lib/__init__.py", b""),
            ("python/Scripts/python.exe", content),
        ]:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    payload = buf.getvalue()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _make_fake_uv_archive(path: Path, *, content: bytes = b"MZ\x90\x00FAKE_UV") -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("uv.exe", content)
    payload = buf.getvalue()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


def test_sha256_file_matches(tmp_path: Path):
    rt = _load_runtime_script()
    p = tmp_path / "thing.bin"
    p.write_bytes(b"hello")
    assert rt.sha256_file(p) == hashlib.sha256(b"hello").hexdigest()


def test_verify_sha256_passes_on_match(tmp_path: Path):
    rt = _load_runtime_script()
    p = tmp_path / "thing.bin"
    p.write_bytes(b"hello")
    rt.verify_sha256(p, hashlib.sha256(b"hello").hexdigest())


def test_verify_sha256_raises_on_mismatch(tmp_path: Path):
    rt = _load_runtime_script()
    p = tmp_path / "thing.bin"
    p.write_bytes(b"hello")
    with pytest.raises(rt.RuntimeAssetError, match="checksum mismatch"):
        rt.verify_sha256(p, "deadbeef" * 8)


def test_verify_sha256_pin_sentinel_is_hard_failure(tmp_path: Path):
    """If the pin literal is the placeholder, fail loud and print the
    real digest. We must not silently accept an unverified runtime."""
    rt = _load_runtime_script()
    p = tmp_path / "thing.bin"
    p.write_bytes(b"hello")
    with pytest.raises(rt.RuntimeAssetError, match="pin missing"):
        rt.verify_sha256(p, "PINNED_AFTER_FIRST_DOWNLOAD")


# ---------------------------------------------------------------------------
# Archive shape
# ---------------------------------------------------------------------------


def test_verify_python_archive_shape_accepts_install_only_layout(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "py.tar.gz"
    _make_fake_python_archive(archive)
    rt.verify_python_archive_shape(archive)


def test_verify_python_archive_shape_rejects_missing_python_exe(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "bad.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo(name="python/Lib/__init__.py")
        info.size = 0
        tf.addfile(info, io.BytesIO(b""))
    archive.write_bytes(buf.getvalue())
    with pytest.raises(rt.RuntimeAssetError, match="missing python/python.exe"):
        rt.verify_python_archive_shape(archive)


def test_verify_python_archive_shape_rejects_non_tar(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "junk.tar.gz"
    archive.write_bytes(b"this is not a tar")
    with pytest.raises(rt.RuntimeAssetError, match="not a tar archive"):
        rt.verify_python_archive_shape(archive)


def test_verify_uv_archive_shape_accepts_top_level(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "uv.zip"
    _make_fake_uv_archive(archive)
    rt.verify_uv_archive_shape(archive)


def test_verify_uv_archive_shape_rejects_missing_uv_exe(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "uv.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.md", "no exe here")
    archive.write_bytes(buf.getvalue())
    with pytest.raises(rt.RuntimeAssetError, match="missing uv.exe"):
        rt.verify_uv_archive_shape(archive)


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


def test_extract_python_archive_lays_python_exe_at_runtime_python(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "py.tar.gz"
    _make_fake_python_archive(archive)
    runtime = tmp_path / "runtime"
    target = rt.extract_python_archive(archive, runtime)
    assert target == runtime / "python"
    assert (target / "python.exe").is_file()


def test_extract_python_archive_idempotent(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "py.tar.gz"
    _make_fake_python_archive(archive)
    runtime = tmp_path / "runtime"
    rt.extract_python_archive(archive, runtime)
    # Second call must not raise — operator may re-run first_setup.
    rt.extract_python_archive(archive, runtime)


def test_extract_uv_archive_places_uv_at_runtime_root(tmp_path: Path):
    rt = _load_runtime_script()
    archive = tmp_path / "uv.zip"
    _make_fake_uv_archive(archive, content=b"MZ\x90uv-payload")
    runtime = tmp_path / "runtime"
    target = rt.extract_uv_archive(archive, runtime)
    assert target == runtime / "uv.exe"
    assert target.read_bytes() == b"MZ\x90uv-payload"


def test_extract_uv_archive_handles_nested_uv_exe(tmp_path: Path):
    """Some uv release zips include a top-level folder; make sure we
    still find uv.exe regardless."""
    rt = _load_runtime_script()
    archive = tmp_path / "uv.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("uv-x86_64-pc-windows-msvc/uv.exe", b"nested")
    archive.write_bytes(buf.getvalue())
    runtime = tmp_path / "runtime"
    target = rt.extract_uv_archive(archive, runtime)
    assert target.read_bytes() == b"nested"


# ---------------------------------------------------------------------------
# Orchestration with stubbed downloads
# ---------------------------------------------------------------------------


def test_download_and_extract_runtime_full_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    rt = _load_runtime_script()

    # Build the fake archives the stubbed opener will return.
    py_archive_payload = io.BytesIO()
    with tarfile.open(fileobj=py_archive_payload, mode="w:gz") as tf:
        for name, data in [
            ("python/python.exe", b"FAKE_PYTHON"),
            ("python/Lib/__init__.py", b""),
        ]:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    py_bytes = py_archive_payload.getvalue()

    uv_archive_payload = io.BytesIO()
    with zipfile.ZipFile(uv_archive_payload, "w") as zf:
        zf.writestr("uv.exe", b"FAKE_UV")
    uv_bytes = uv_archive_payload.getvalue()

    py_sha = hashlib.sha256(py_bytes).hexdigest()
    uv_sha = hashlib.sha256(uv_bytes).hexdigest()

    monkeypatch.setitem(rt.PYTHON_BUILD_STANDALONE, "sha256", py_sha)
    monkeypatch.setitem(rt.UV_WINDOWS, "sha256", uv_sha)

    class _StubResp:
        def __init__(self, payload: bytes):
            self._buf = io.BytesIO(payload)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, n: int = -1) -> bytes:
            return self._buf.read(n)

    def _fake_opener(url: str):
        if "python-build-standalone" in url:
            return _StubResp(py_bytes)
        if "uv-x86_64-pc-windows-msvc" in url or "/uv/" in url:
            return _StubResp(uv_bytes)
        raise AssertionError(f"unexpected url: {url}")

    runtime_dir = tmp_path / "runtime"
    cache = tmp_path / "cache"

    manifest = rt.download_and_extract_runtime(
        runtime_dir=runtime_dir,
        cache_dir=cache,
        opener=_fake_opener,
    )

    assert manifest.python_dir == runtime_dir / "python"
    assert (manifest.python_dir / "python.exe").is_file()
    assert manifest.uv_exe == runtime_dir / "uv.exe"
    assert manifest.uv_exe.read_bytes() == b"FAKE_UV"


def test_download_and_extract_runtime_fails_on_pin_sentinel(tmp_path: Path):
    """Without monkeypatching the pin, the script must refuse to ship
    the runtime."""
    rt = _load_runtime_script()

    py_archive_payload = io.BytesIO()
    with tarfile.open(fileobj=py_archive_payload, mode="w:gz") as tf:
        info = tarfile.TarInfo(name="python/python.exe")
        info.size = 4
        tf.addfile(info, io.BytesIO(b"FAKE"))
    py_bytes = py_archive_payload.getvalue()

    class _StubResp:
        def __init__(self, payload: bytes):
            self._buf = io.BytesIO(payload)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, n: int = -1) -> bytes:
            return self._buf.read(n)

    def _fake_opener(url: str):
        return _StubResp(py_bytes)

    with pytest.raises(rt.RuntimeAssetError, match="pin missing"):
        rt.download_and_extract_runtime(
            runtime_dir=tmp_path / "runtime",
            cache_dir=tmp_path / "cache",
            opener=_fake_opener,
        )


# ---------------------------------------------------------------------------
# build_windows_zip integration
# ---------------------------------------------------------------------------


def test_collect_zip_members_includes_runtime_when_present(tmp_path: Path):
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    runtime = fake_repo / "runtime"
    (runtime / "python").mkdir(parents=True)
    (runtime / "python" / "python.exe").write_bytes(b"FAKE_PY")
    (runtime / "uv.exe").write_bytes(b"FAKE_UV")
    (fake_repo / "src" / "eidp").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")

    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")

    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}
    assert "runtime/python/python.exe" in arcs
    assert "runtime/uv.exe" in arcs


def test_collect_zip_members_omits_runtime_when_absent(tmp_path: Path):
    """No runtime/ directory means the manifest just doesn't have it.
    assert_runtime_present is the gate, not the collector."""
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    (fake_repo / "src" / "eidp").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")
    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")
    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}
    assert not any(a.startswith("runtime/") for a in arcs)


def test_assert_runtime_present_passes_when_files_exist(tmp_path: Path):
    bw = _load_build_script()
    repo = tmp_path / "repo"
    (repo / "runtime" / "python").mkdir(parents=True)
    (repo / "runtime" / "python" / "python.exe").write_bytes(b"x")
    (repo / "runtime" / "uv.exe").write_bytes(b"y")
    bw.assert_runtime_present(repo)  # no raise


def test_assert_runtime_present_raises_when_missing(tmp_path: Path):
    bw = _load_build_script()
    with pytest.raises(RuntimeError, match="runtime files missing"):
        bw.assert_runtime_present(tmp_path / "no-such-repo")


def test_assert_runtime_present_raises_when_uv_missing(tmp_path: Path):
    """Partial runtime is still a failure — both pieces required."""
    bw = _load_build_script()
    repo = tmp_path / "repo"
    (repo / "runtime" / "python").mkdir(parents=True)
    (repo / "runtime" / "python" / "python.exe").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="uv.exe"):
        bw.assert_runtime_present(repo)


# ---------------------------------------------------------------------------
# Cross-platform safety — never accept a darwin/linux runtime by accident
# ---------------------------------------------------------------------------


def test_pinned_python_release_targets_windows_x86_64():
    rt = _load_runtime_script()
    name = rt.PYTHON_BUILD_STANDALONE["filename"]
    assert "windows-msvc" in name, "must target Windows MSVC build"
    assert "x86_64" in name, "must be x86_64 (operator PCs are Intel/AMD)"
    assert "install_only" in name, "must be install_only flavor with python/ at root"
    # Negative — confirm we are NOT pulling Linux or macOS variants.
    for fragment in ("linux", "darwin", "apple"):
        assert fragment not in name, f"runtime archive must not be {fragment}"


def test_pinned_uv_release_targets_windows():
    rt = _load_runtime_script()
    name = rt.UV_WINDOWS["filename"]
    assert "windows" in name
    assert "x86_64" in name
    for fragment in ("linux", "darwin", "apple"):
        assert fragment not in name
