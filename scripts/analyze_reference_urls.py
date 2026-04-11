#!/usr/bin/env python3
"""
Analyze reference Japanese school websites for PDF publishing patterns.
Research-only: fetches HTML pages and analyzes PDF link structures.
Does NOT bulk-download PDFs.
"""

import httpx
import json
import re
import sys
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

REFERENCE_URLS = [
    {
        "name": "Toho Gakuen",
        "url": "https://www.tohogakuen.ac.jp/about/valuation/",
        "domain": "tohogakuen.ac.jp",
    },
    {
        "name": "JEC (Japan Electronics College)",
        "url": "https://www.jec.ac.jp/school-outline/disclose/",
        "domain": "jec.ac.jp",
    },
    {
        "name": "TCA (Tokyo Communication Arts)",
        "url": "https://www.tca.ac.jp/school/public_info/",
        "domain": "tca.ac.jp",
    },
    {
        "name": "NKZ (Nakamura Gakuen)",
        "url": "https://www.nkz.ac.jp/clginfo/thinfo.html",
        "domain": "nkz.ac.jp",
    },
]

TARGET_KEYWORDS = [
    "修学支援",
    "機関要件",
    "確認申請",
    "高等教育",
    "新制度",
    "情報公開",
    "学校情報",
    "財務情報",
    "学校評価",
    "自己評価",
    "自己点検",
    "教育情報",
    "学校関係者評価",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def fetch_page(url: str, client: httpx.Client) -> dict:
    """Fetch a page and return status info + HTML content."""
    result = {
        "url": url,
        "status_code": None,
        "content_type": None,
        "html": None,
        "error": None,
        "headers": {},
        "redirect_chain": [],
    }
    try:
        resp = client.get(url, follow_redirects=True, timeout=30.0)
        result["status_code"] = resp.status_code
        result["content_type"] = resp.headers.get("content-type", "")
        result["headers"] = dict(resp.headers)
        result["html"] = resp.text
        # Track redirects
        if resp.history:
            result["redirect_chain"] = [str(r.url) for r in resp.history]
    except Exception as e:
        result["error"] = str(e)
    return result


def fetch_robots_txt(domain: str, client: httpx.Client) -> str:
    """Fetch robots.txt for a domain."""
    try:
        resp = client.get(f"https://www.{domain}/robots.txt", timeout=15.0)
        if resp.status_code == 200:
            return resp.text
        return f"[HTTP {resp.status_code}]"
    except Exception as e:
        return f"[Error: {e}]"


def extract_pdf_links(html: str, base_url: str) -> list[dict]:
    """Extract all PDF-related links from HTML."""
    soup = BeautifulSoup(html, "lxml")
    pdf_links = []

    # Method 1: <a> tags with href ending in .pdf or containing .pdf
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if ".pdf" in href.lower():
            full_url = urljoin(base_url, href)
            anchor_text = a_tag.get_text(strip=True)

            # Find surrounding heading
            heading_text = ""
            parent = a_tag.parent
            for _ in range(10):
                if parent is None:
                    break
                heading = parent.find_previous(re.compile(r"^h[1-6]$"))
                if heading:
                    heading_text = heading.get_text(strip=True)
                    break
                parent = parent.parent

            # Also check for nearby headings in sibling context
            if not heading_text:
                for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    h = a_tag.find_previous(tag)
                    if h:
                        heading_text = h.get_text(strip=True)
                        break

            # Extract URL path pattern
            parsed = urlparse(full_url)
            path_pattern = parsed.path

            # Check keyword matches
            combined_text = f"{anchor_text} {heading_text} {path_pattern}"
            matched_keywords = [
                kw for kw in TARGET_KEYWORDS if kw in combined_text
            ]

            pdf_links.append({
                "url": full_url,
                "anchor_text": anchor_text,
                "heading_text": heading_text,
                "path_pattern": path_pattern,
                "matched_keywords": matched_keywords,
                "is_likely_target": len(matched_keywords) >= 1,
                "source": "a_tag",
            })

    # Method 2: <iframe> with PDF src
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"]
        if ".pdf" in src.lower():
            full_url = urljoin(base_url, src)
            parsed = urlparse(full_url)
            pdf_links.append({
                "url": full_url,
                "anchor_text": "[iframe embed]",
                "heading_text": "",
                "path_pattern": parsed.path,
                "matched_keywords": [],
                "is_likely_target": False,
                "source": "iframe",
            })

    # Method 3: <embed> with PDF src
    for embed in soup.find_all("embed", src=True):
        src = embed["src"]
        if ".pdf" in src.lower():
            full_url = urljoin(base_url, src)
            parsed = urlparse(full_url)
            pdf_links.append({
                "url": full_url,
                "anchor_text": "[embed]",
                "heading_text": "",
                "path_pattern": parsed.path,
                "matched_keywords": [],
                "is_likely_target": False,
                "source": "embed",
            })

    # Method 4: <object> with PDF data
    for obj in soup.find_all("object", data=True):
        data = obj["data"]
        if ".pdf" in data.lower():
            full_url = urljoin(base_url, data)
            parsed = urlparse(full_url)
            pdf_links.append({
                "url": full_url,
                "anchor_text": "[object embed]",
                "heading_text": "",
                "path_pattern": parsed.path,
                "matched_keywords": [],
                "is_likely_target": False,
                "source": "object",
            })

    return pdf_links


def check_js_rendering(html: str) -> dict:
    """Check if the page appears to require JavaScript for rendering PDF links."""
    soup = BeautifulSoup(html, "lxml")
    indicators = {
        "has_noscript": bool(soup.find("noscript")),
        "has_react_root": bool(soup.find(id="root") or soup.find(id="__next")),
        "has_vue_app": bool(soup.find(id="app")),
        "has_angular": bool(soup.find(attrs={"ng-app": True})),
        "script_count": len(soup.find_all("script")),
        "has_data_attributes": bool(soup.find(attrs={"data-react": True})),
        "body_has_content": len(soup.body.get_text(strip=True)) > 100 if soup.body else False,
        "pdf_links_in_raw_html": ".pdf" in html.lower(),
    }
    indicators["likely_js_rendered"] = (
        (indicators["has_react_root"] or indicators["has_vue_app"] or indicators["has_angular"])
        and not indicators["pdf_links_in_raw_html"]
    )
    return indicators


def test_pdf_downloadability(pdf_url: str, client: httpx.Client) -> dict:
    """Test if a PDF URL is directly downloadable (HEAD request only)."""
    result = {
        "url": pdf_url,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "downloadable": False,
        "error": None,
        "anti_scraping": None,
    }
    try:
        # Try HEAD first
        resp = client.head(pdf_url, follow_redirects=True, timeout=15.0)
        result["status_code"] = resp.status_code
        result["content_type"] = resp.headers.get("content-type", "")
        result["content_length"] = resp.headers.get("content-length", "")

        if resp.status_code == 200 and "pdf" in result["content_type"].lower():
            result["downloadable"] = True
        elif resp.status_code == 403:
            result["anti_scraping"] = "403 Forbidden - possible anti-scraping"
        elif resp.status_code == 405:
            # HEAD not allowed, try GET with range header
            resp2 = client.get(
                pdf_url,
                headers={"Range": "bytes=0-1024"},
                follow_redirects=True,
                timeout=15.0,
            )
            result["status_code"] = resp2.status_code
            result["content_type"] = resp2.headers.get("content-type", "")
            if resp2.status_code in (200, 206) and "pdf" in result["content_type"].lower():
                result["downloadable"] = True

        # Check for Cloudflare
        server = resp.headers.get("server", "").lower()
        if "cloudflare" in server:
            result["anti_scraping"] = (result.get("anti_scraping") or "") + " [Cloudflare detected]"

    except Exception as e:
        result["error"] = str(e)

    return result


def analyze_page_structure(html: str) -> dict:
    """Analyze the page structure for common layout patterns."""
    soup = BeautifulSoup(html, "lxml")

    # Check for common disclosure page patterns
    patterns = {
        "has_table_layout": bool(soup.find("table")),
        "has_list_layout": bool(soup.find("ul") or soup.find("ol")),
        "has_accordion": bool(
            soup.find(class_=re.compile(r"accordion|collapse|toggle", re.I))
            or soup.find(attrs={"data-toggle": "collapse"})
        ),
        "has_tab_layout": bool(
            soup.find(class_=re.compile(r"tab", re.I))
        ),
        "heading_count": len(soup.find_all(re.compile(r"^h[1-6]$"))),
        "total_links": len(soup.find_all("a", href=True)),
        "pdf_links_count": len([
            a for a in soup.find_all("a", href=True)
            if ".pdf" in a.get("href", "").lower()
        ]),
    }

    # Extract headings for context
    headings = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        headings.append({
            "level": tag.name,
            "text": tag.get_text(strip=True),
        })
    patterns["headings"] = headings

    return patterns


def analyze_site(site: dict, client: httpx.Client) -> dict:
    """Full analysis of a single site."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {site['name']} ({site['url']})")
    print(f"{'='*60}")

    result = {
        "name": site["name"],
        "url": site["url"],
        "domain": site["domain"],
    }

    # 1. Fetch robots.txt
    print("  [1/5] Fetching robots.txt...")
    result["robots_txt"] = fetch_robots_txt(site["domain"], client)
    time.sleep(1)

    # 2. Fetch the page
    print("  [2/5] Fetching page HTML...")
    page_result = fetch_page(site["url"], client)
    result["page_fetch"] = {
        "status_code": page_result["status_code"],
        "content_type": page_result["content_type"],
        "error": page_result["error"],
        "redirect_chain": page_result["redirect_chain"],
        "html_length": len(page_result["html"]) if page_result["html"] else 0,
    }

    if not page_result["html"]:
        print(f"  ERROR: Could not fetch page: {page_result['error']}")
        return result

    # 3. Analyze page structure
    print("  [3/5] Analyzing page structure...")
    result["page_structure"] = analyze_page_structure(page_result["html"])
    result["js_rendering"] = check_js_rendering(page_result["html"])

    # 4. Extract PDF links
    print("  [4/5] Extracting PDF links...")
    pdf_links = extract_pdf_links(page_result["html"], site["url"])
    result["pdf_links"] = pdf_links
    result["pdf_link_count"] = len(pdf_links)
    result["likely_target_count"] = sum(1 for p in pdf_links if p["is_likely_target"])

    print(f"    Found {len(pdf_links)} PDF links ({result['likely_target_count']} likely targets)")
    for link in pdf_links:
        marker = " [TARGET]" if link["is_likely_target"] else ""
        print(f"    - {link['anchor_text'][:60]}{marker}")
        print(f"      URL: {link['url'][:80]}")

    # 5. Test downloadability of first few PDF links
    print("  [5/5] Testing PDF downloadability...")
    download_tests = []
    test_urls = set()
    for link in pdf_links[:5]:  # Test max 5 per site
        if link["url"] not in test_urls:
            test_urls.add(link["url"])
            dl_result = test_pdf_downloadability(link["url"], client)
            download_tests.append(dl_result)
            status = "OK" if dl_result["downloadable"] else f"FAIL ({dl_result.get('status_code')})"
            print(f"    {status}: {link['url'][:70]}")
            time.sleep(0.5)

    result["download_tests"] = download_tests

    return result


def main():
    results = []

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for site in REFERENCE_URLS:
            try:
                site_result = analyze_site(site, client)
                results.append(site_result)
            except Exception as e:
                print(f"  FATAL ERROR for {site['name']}: {e}")
                results.append({
                    "name": site["name"],
                    "url": site["url"],
                    "error": str(e),
                })
            time.sleep(2)  # Polite delay between sites

    # Output JSON results
    output_path = "/Users/shunmei/workspace/EIDP/scripts/reference_url_analysis_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\nResults saved to: {output_path}")
    print(f"\nTotal sites analyzed: {len(results)}")
    for r in results:
        if "error" in r and isinstance(r.get("error"), str):
            print(f"  {r['name']}: ERROR - {r['error']}")
        else:
            count = r.get("pdf_link_count", 0)
            targets = r.get("likely_target_count", 0)
            print(f"  {r['name']}: {count} PDFs found, {targets} likely targets")

    return results


if __name__ == "__main__":
    main()
