# ruff: noqa: N999
"""Streamlit multipage wrapper for the extraction queue."""

from eidp.web.pages.extraction_queue import render_extraction_queue_page

if __name__ == "__main__":
    render_extraction_queue_page()
