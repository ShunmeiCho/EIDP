"""Shared exceptions for school URL auto-discovery."""

from __future__ import annotations


class ScraplingUnavailableError(RuntimeError):
    """Raised when the optional Scrapling runtime is not installed."""
