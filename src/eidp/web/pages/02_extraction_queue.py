# ruff: noqa: N999
"""Streamlit multipage wrapper for the extraction queue."""

from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.views.extraction_queue import render_extraction_queue_page

if __name__ == "__main__":
    identity = bootstrap_web_request()
    render_extraction_queue_page(identity=identity)
