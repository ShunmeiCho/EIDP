# ruff: noqa: N999
"""Streamlit multipage wrapper for PDF intake."""

from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.pages.pdf_intake import render_pdf_intake_page

if __name__ == "__main__":
    identity = bootstrap_web_request()
    render_pdf_intake_page(identity=identity)
