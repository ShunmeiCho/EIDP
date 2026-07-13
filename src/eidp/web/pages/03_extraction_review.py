# ruff: noqa: N999
"""Streamlit multipage wrapper for extraction review."""

from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.pages.extraction_review import render_extraction_review_page

if __name__ == "__main__":
    identity = bootstrap_web_request()
    render_extraction_review_page(identity=identity)
