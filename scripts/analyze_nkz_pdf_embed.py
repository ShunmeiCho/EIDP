#!/usr/bin/env python3
"""
Analyze NKZ PDF embedding pattern and test downloadability.
Also debug TCA PDF detection.
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


def analyze_nkz_pdf_embedding():
    """Analyze how NKZ embeds PDFs in subpages."""
    print("="*70)
    print("NKZ PDF Embedding Pattern Analysis")
    print("="*70)

    url = "https://www.nkz.ac.jp/clginfo/th/thZ-studyspt_13.html"

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        resp = client.get(url)
        html = resp.text

        # Print the entire HTML to understand the structure
        print(f"\nFull HTML of target subpage ({len(html)} chars):")
        print("-"*70)
        print(html)
        print("-"*70)

        # Extract the PDF reference
        pdf_refs = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', html, re.I)
        print(f"\nPDF references found in HTML: {pdf_refs}")

        # Construct the full PDF URL
        if pdf_refs:
            pdf_url = urljoin(url, pdf_refs[0])
            print(f"\nConstructed PDF URL: {pdf_url}")

            # Test downloadability
            print("\nTesting PDF downloadability...")
            try:
                resp2 = client.head(pdf_url, follow_redirects=True, timeout=15.0)
                print(f"  HEAD status: {resp2.status_code}")
                print(f"  Content-Type: {resp2.headers.get('content-type')}")
                print(f"  Content-Length: {resp2.headers.get('content-length')}")

                if resp2.status_code == 405:
                    print("  HEAD not allowed, trying GET...")
                    resp3 = client.get(
                        pdf_url,
                        headers={"Range": "bytes=0-1024"},
                        follow_redirects=True,
                        timeout=15.0,
                    )
                    print(f"  GET status: {resp3.status_code}")
                    print(f"  Content-Type: {resp3.headers.get('content-type')}")
            except Exception as e:
                print(f"  ERROR: {e}")


def debug_tca_detection():
    """Debug why TCA returns 0 in the initial script."""
    print("\n" + "="*70)
    print("TCA PDF Detection Debug")
    print("="*70)

    url = "https://www.tca.ac.jp/school/public_info/"

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        resp = client.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Check: does a[href$=".pdf"] work?
        css_selector_results = soup.select('a[href$=".pdf"]')
        print(f"\nCSS selector a[href$='.pdf']: {len(css_selector_results)} results")

        # Check: what about with query strings?
        css_selector_results2 = soup.select('a[href*=".pdf"]')
        print(f"CSS selector a[href*='.pdf']: {len(css_selector_results2)} results")

        # Check with BeautifulSoup find_all
        all_a = soup.find_all("a", href=True)
        pdf_count = 0
        for a in all_a:
            href = a["href"]
            if ".pdf" in href.lower():
                pdf_count += 1

        print(f"find_all with .pdf check: {pdf_count} results")

        # Print first 5 PDF hrefs to see the pattern
        print("\nFirst 5 PDF hrefs:")
        count = 0
        for a in all_a:
            href = a["href"]
            if ".pdf" in href.lower():
                print(f"  href='{href}'")
                print(f"  text='{a.get_text(strip=True)}'")
                count += 1
                if count >= 5:
                    break

        # The issue might be relative vs absolute URLs
        # Let's check if the initial script's href check was correct
        print(f"\nURL starts with 'http': {any(a['href'].startswith('http') and '.pdf' in a['href'].lower() for a in all_a)}")
        print(f"URL starts with '/': {any(a['href'].startswith('/') and '.pdf' in a['href'].lower() for a in all_a)}")
        print(f"URL is relative (no /): {any(not a['href'].startswith('/') and not a['href'].startswith('http') and '.pdf' in a['href'].lower() for a in all_a)}")

        # Check the specific target document link
        print("\nLooking for target document links:")
        for a in all_a:
            text = a.get_text(strip=True)
            href = a["href"]
            if any(kw in text for kw in ["修学支援", "確認申請", "高等教育"]):
                full_url = urljoin(url, href)
                print(f"  [{text[:60]}]")
                print(f"  href='{href}'")
                print(f"  full_url='{full_url}'")

                # Test downloadability
                try:
                    resp2 = client.head(full_url, follow_redirects=True, timeout=15.0)
                    print(f"  Status: {resp2.status_code}, CT: {resp2.headers.get('content-type')}")
                except Exception as e:
                    print(f"  ERROR: {e}")


analyze_nkz_pdf_embedding()
debug_tca_detection()
