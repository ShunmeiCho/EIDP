from __future__ import annotations

import json

from eidp.review.app import DETAIL_PAGES, PAGE_AUDIT_LOG, PAGE_SETTINGS, QUICK_PAGES, _build_info_caption


def test_build_info_caption_reads_packaged_commit(tmp_path):
    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "app": "EIDP",
                "built_at_utc": "2026-05-06T12:00:00+00:00",
                "git_commit": "1234567890abcdef1234567890abcdef12345678",
                "git_branch": "release/test",
                "git_dirty": "false",
            }
        ),
        encoding="utf-8",
    )

    caption = _build_info_caption(tmp_path)

    assert "build: 1234567" in caption
    assert "branch: release/test" in caption
    assert "built: 2026-05-06T12:00:00+00:00" in caption


def test_build_info_caption_marks_dirty_build(tmp_path):
    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "app": "EIDP",
                "built_at_utc": "2026-05-06T12:00:00+00:00",
                "git_commit": "1234567890abcdef1234567890abcdef12345678",
                "git_branch": "release/test",
                "git_dirty": "true",
            }
        ),
        encoding="utf-8",
    )

    assert "build: 1234567 dirty" in _build_info_caption(tmp_path)


def test_build_info_caption_falls_back_for_source_checkout(tmp_path):
    assert _build_info_caption(tmp_path) == "build: source checkout"


def test_settings_is_visible_in_quick_navigation():
    quick_ids = [page_id for page_id, _label in QUICK_PAGES]
    detail_ids = [page_id for page_id, _label in DETAIL_PAGES]

    assert PAGE_SETTINGS in quick_ids
    assert PAGE_SETTINGS not in detail_ids
    assert PAGE_AUDIT_LOG in detail_ids
