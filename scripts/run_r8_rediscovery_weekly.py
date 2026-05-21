"""Backward-compatible wrapper for the renamed weekly target-year runner.

The production entrypoint is now ``run_weekly_target_year_discovery.py``.
Keep this wrapper so previously deployed Task Scheduler entries and older ZIP
validators fail softly instead of losing the weekly run.
"""

from __future__ import annotations

from run_weekly_target_year_discovery import main

if __name__ == "__main__":
    main()
