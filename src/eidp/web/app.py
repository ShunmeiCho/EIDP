"""Streamlit entry point for the Linux/Web PDF intake MVP.

Launch with:
    streamlit run src/eidp/web/app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from eidp.config import settings
from eidp.logging_config import configure_logging
from eidp.web.bootstrap import bootstrap_web_request
from eidp.web.pages.pdf_intake import render_pdf_intake_page


def main() -> None:
    configure_logging(app_root=Path(settings.app_root))
    st.set_page_config(page_title="EIDP PDF Intake", layout="wide")
    identity = bootstrap_web_request()
    render_pdf_intake_page(identity=identity, intake_root=Path(settings.data_dir) / "web-intake")


if __name__ == "__main__":
    main()
