"""URL canonicalization shared by school URL discovery components."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_candidate_url(url: str) -> str:
    """Return a stable URL key for dedup/idempotency.

    The crawler gets the same official homepage through SERP variants such as
    trailing slash, fragment, or mixed-case host. Normalize only the pieces
    that are safe for school homepage URLs; keep query parameters but sort
    them for stable comparisons.
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    elif scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]

    path = re.sub(r"/+", "/", parsed.path or "")
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")

    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))
