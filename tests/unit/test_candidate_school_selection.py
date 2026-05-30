"""Candidate selection must treat PDF-body school name as the primary signal.

Dense multi-brand corporate disclosure pages (Sanko / O-Hara / Nihon Denshi
style) list dozens of sibling-school application PDFs on one page. Link/anchor
text is an unreliable attribution signal there: a generic ``申請書(PDF)`` anchor,
or an anchor that names a *different* sibling, routinely points at the wrong
school. The PDF body, once classified (``detected_school_name``), is the
authoritative signal for which school a form belongs to.

These tests pin the contract that ``_prioritize_viable_candidates`` ranks a
body-confirmed candidate ABOVE a link-text-only match, and pushes a
body-contradicted candidate (body names a *different* identifiable school) to
the back -- while preserving the existing link-text ordering when no body
classification is available yet.
"""

from eidp.scraper.pdf_discovery import PdfCandidate, _prioritize_viable_candidates

TARGET = "東京デザイン専門学校"
SIBLING = "東京コミュニケーションアート専門学校"
FORM_HINT = "様式第2号 申請書"


def _cand(*, url: str, anchor: str, body: str = "") -> PdfCandidate:
    return PdfCandidate(
        pdf_url=url,
        page_url="https://group.example.ac.jp/disclosure/",
        anchor_text=anchor,
        pattern_type="direct",
        detected_school_name=body,
    )


def test_body_confirmed_candidate_outranks_link_text_only_match():
    """Body match for the target must beat an anchor that merely names it."""
    link_says_target_body_says_sibling = _cand(
        url="https://group.example.ac.jp/files/2026-shinsei-a.pdf",
        anchor=f"{TARGET} {FORM_HINT}",
        body=SIBLING,
    )
    anchor_generic_body_says_target = _cand(
        url="https://group.example.ac.jp/files/2026-shinsei-b.pdf",
        anchor=FORM_HINT,
        body=TARGET,
    )

    ordered, _dropped = _prioritize_viable_candidates(
        [link_says_target_body_says_sibling, anchor_generic_body_says_target],
        target_year=2026,
        school_name=TARGET,
        school_names=[TARGET],
    )

    assert ordered[0].pdf_url.endswith("b.pdf"), (
        "Body-confirmed target form must be downloaded first; got "
        f"{ordered[0].pdf_url}"
    )
    # The body-contradicted candidate (body names a different school) must sink.
    assert ordered[-1].pdf_url.endswith("a.pdf")


def test_body_match_beats_neutral_candidate_without_link_match():
    body_target = _cand(
        url="https://group.example.ac.jp/files/b.pdf",
        anchor=FORM_HINT,
        body=TARGET,
    )
    neutral = _cand(
        url="https://group.example.ac.jp/files/n.pdf",
        anchor=FORM_HINT,
        body="",
    )

    ordered, _ = _prioritize_viable_candidates(
        [neutral, body_target],
        target_year=2026,
        school_name=TARGET,
        school_names=[TARGET],
    )

    assert ordered[0].pdf_url.endswith("b.pdf")


def test_no_body_info_preserves_link_text_ordering():
    """When no candidate is classified yet, link-text match still orders first."""
    link_match = _cand(
        url="https://group.example.ac.jp/files/match.pdf",
        anchor=f"{TARGET} {FORM_HINT}",
        body="",
    )
    no_match = _cand(
        url="https://group.example.ac.jp/files/other.pdf",
        anchor=FORM_HINT,
        body="",
    )

    ordered, _ = _prioritize_viable_candidates(
        [no_match, link_match],
        target_year=2026,
        school_name=TARGET,
        school_names=[TARGET],
    )

    assert ordered[0].pdf_url.endswith("match.pdf")
