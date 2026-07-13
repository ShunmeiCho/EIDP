# ruff: noqa: N999
"""Streamlit multipage wrapper for review diff."""

from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.pages.review_diff import render_review_diff_page

if __name__ == "__main__":
    identity = bootstrap_web_request()
    render_review_diff_page(identity=identity)
