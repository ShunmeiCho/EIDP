#!/usr/bin/env python3
"""
Deep analysis of TCA and NKZ sites that returned 0 PDF links.
Check for JS rendering, alternative link patterns, and page content.
"""

import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def deep_analyze(url: str, name: str):
    print(f"\n{'='*70}")
    print(f"Deep Analysis: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        resp = client.get(url)
        html = resp.text
        print(f"\nStatus: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print(f"HTML length: {len(html)} chars")

        soup = BeautifulSoup(html, "lxml")

        # Check page title
        title = soup.find("title")
        print(f"Title: {title.get_text() if title else 'N/A'}")

        # Check for meta refresh or redirects
        meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
        if meta_refresh:
            print(f"META REFRESH: {meta_refresh.get('content')}")

        # Count content in body
        body = soup.find("body")
        if body:
            body_text = body.get_text(strip=True)
            print(f"Body text length: {len(body_text)} chars")
            print(f"Body text preview: {body_text[:300]}...")
        else:
            print("NO BODY TAG FOUND")

        # Check all links
        all_links = soup.find_all("a", href=True)
        print(f"\nTotal links: {len(all_links)}")

        # Check for any file download links
        file_links = []
        for a in all_links:
            href = a["href"].lower()
            text = a.get_text(strip=True)
            if any(ext in href for ext in [".pdf", ".doc", ".xls", ".xlsx", ".csv", ".zip"]):
                file_links.append({"href": a["href"], "text": text})
            # Also check for download attributes
            if a.get("download"):
                file_links.append({"href": a["href"], "text": text, "has_download_attr": True})
            # Check for onclick handlers that might trigger downloads
            if a.get("onclick") and "pdf" in a.get("onclick", "").lower():
                file_links.append({"href": a["href"], "text": text, "onclick": a["onclick"]})

        print(f"File download links found: {len(file_links)}")
        for fl in file_links:
            print(f"  - {fl}")

        # Check for iframes
        iframes = soup.find_all("iframe")
        print(f"\nIframes: {len(iframes)}")
        for iframe in iframes:
            print(f"  src: {iframe.get('src', 'N/A')}")

        # Check for embeds/objects
        embeds = soup.find_all(["embed", "object"])
        print(f"Embeds/Objects: {len(embeds)}")
        for e in embeds:
            print(f"  {e.name}: src={e.get('src', e.get('data', 'N/A'))}")

        # Check for JavaScript that loads PDFs dynamically
        scripts = soup.find_all("script")
        print(f"\nScript tags: {len(scripts)}")
        pdf_in_scripts = False
        for script in scripts:
            text = script.string or ""
            if ".pdf" in text.lower():
                pdf_in_scripts = True
                # Find the relevant lines
                for line in text.split("\n"):
                    if ".pdf" in line.lower():
                        print(f"  JS PDF ref: {line.strip()[:120]}")

        if not pdf_in_scripts:
            print("  No .pdf references found in inline scripts")

        # Check for external JS files that might contain PDF URLs
        external_scripts = [s.get("src") for s in scripts if s.get("src")]
        print(f"\nExternal script files: {len(external_scripts)}")
        for src in external_scripts:
            full_url = urljoin(url, src)
            print(f"  {full_url}")

        # Check raw HTML for .pdf patterns not caught by BeautifulSoup
        pdf_pattern = re.compile(r'["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE)
        raw_pdf_matches = pdf_pattern.findall(html)
        print(f"\nRaw HTML .pdf pattern matches: {len(raw_pdf_matches)}")
        for match in raw_pdf_matches:
            print(f"  {match[:120]}")

        # Check for data attributes that might contain PDF URLs
        data_attrs = soup.find_all(attrs=lambda x: x and any(
            ".pdf" in str(v).lower() for v in (x.values() if hasattr(x, "values") else [])
        ))
        print(f"\nElements with .pdf in data attributes: {len(data_attrs)}")
        for elem in data_attrs:
            print(f"  {elem.name}: {dict(elem.attrs)}")

        # Print all headings for context
        print("\nPage headings:")
        for h in soup.find_all(re.compile(r"^h[1-6]$")):
            print(f"  {h.name}: {h.get_text(strip=True)[:80]}")

        # Check for common JS frameworks
        print("\nFramework indicators:")
        print(f"  React root (#root/#__next): {bool(soup.find(id='root') or soup.find(id='__next'))}")
        print(f"  Vue (#app): {bool(soup.find(id='app'))}")
        print(f"  Angular (ng-app): {bool(soup.find(attrs={'ng-app': True}))}")
        print(f"  jQuery: {'jquery' in html.lower()}")

        # Check for noscript content
        noscripts = soup.find_all("noscript")
        if noscripts:
            print(f"\nNoscript tags: {len(noscripts)}")
            for ns in noscripts:
                print(f"  Content: {ns.get_text(strip=True)[:100]}")

        # Dump a sample of the main content area
        main_content = soup.find("main") or soup.find(class_=re.compile(r"main|content|entry", re.I))
        if main_content:
            print(f"\nMain content area preview:")
            print(main_content.get_text(strip=True)[:500])
        else:
            print("\nNo main/content area found. Body preview:")
            if body:
                print(body.get_text(strip=True)[:500])

        # Check link targets specifically
        print(f"\nAll link hrefs containing key terms:")
        for a in all_links:
            href = a["href"]
            text = a.get_text(strip=True)
            if any(kw in href.lower() or kw in text for kw in [
                "pdf", "download", "file", "document",
                "info", "public", "disclose", "joho",
                "koukai", "hyouka", "shien", "youken"
            ]):
                print(f"  [{text[:40]}] -> {href[:80]}")


# Analyze TCA
deep_analyze("https://www.tca.ac.jp/school/public_info/", "TCA")

# Analyze NKZ
deep_analyze("https://www.nkz.ac.jp/clginfo/thinfo.html", "NKZ")
