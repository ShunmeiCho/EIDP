# ruff: noqa: N999
"""Streamlit multipage wrapper for external double-check."""

from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.pages.double_check import render_double_check_page

if __name__ == "__main__":
    identity = bootstrap_web_request()
    render_double_check_page(identity=identity)
