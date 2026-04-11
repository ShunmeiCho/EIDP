#!/usr/bin/env python3
"""
Analyze NKZ subpages to find how they link to PDFs.
NKZ uses HTML landing pages that then link to PDFs.
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

BASE_URL = "https://www.nkz.ac.jp/clginfo/thinfo.html"


def main():
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        # Fetch main page
        resp = client.get(BASE_URL)
        soup = BeautifulSoup(resp.text, "lxml")

        # Get all links from the page
        all_links = soup.find_all("a", href=True)
        print(f"Total links on NKZ main page: {len(all_links)}")
        print("\nAll links:")
        for a in all_links:
            href = a["href"]
            text = a.get_text(strip=True)
            full_url = urljoin(BASE_URL, href)
            print(f"  [{text[:50]}] -> {full_url}")

        # Find links that look like info disclosure subpages
        subpage_links = []
        for a in all_links:
            href = a["href"]
            text = a.get_text(strip=True)
            if any(kw in text for kw in [
                "事業報告", "自己評価", "学校関係者", "学則",
                "修学支援", "確認申請", "基本情報", "学科別",
            ]):
                full_url = urljoin(BASE_URL, href)
                subpage_links.append({"url": full_url, "text": text})

        print(f"\nInfo disclosure subpages: {len(subpage_links)}")

        # Fetch a sample subpage to see how PDFs are linked
        for link in subpage_links[:5]:
            print(f"\n{'='*60}")
            print(f"Fetching subpage: {link['text']}")
            print(f"URL: {link['url']}")
            print(f"{'='*60}")

            try:
                resp2 = client.get(link["url"])
                html2 = resp2.text
                soup2 = BeautifulSoup(html2, "lxml")

                print(f"Status: {resp2.status_code}")
                print(f"HTML length: {len(html2)}")

                # Check for PDF links
                pdf_links = []
                for a2 in soup2.find_all("a", href=True):
                    if ".pdf" in a2["href"].lower():
                        pdf_links.append({
                            "url": urljoin(link["url"], a2["href"]),
                            "text": a2.get_text(strip=True),
                        })

                print(f"PDF links found: {len(pdf_links)}")
                for pl in pdf_links:
                    print(f"  [{pl['text'][:60]}] -> {pl['url'][:80]}")

                # Check iframes / embeds
                for iframe in soup2.find_all("iframe"):
                    print(f"  iframe: src={iframe.get('src', 'N/A')[:80]}")

                # Check raw HTML for PDF patterns
                raw_pdfs = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', html2, re.I)
                if raw_pdfs and not pdf_links:
                    print(f"  Raw HTML PDF refs: {len(raw_pdfs)}")
                    for rp in raw_pdfs:
                        print(f"    {rp[:80]}")

                # Check body content
                body = soup2.find("body")
                if body:
                    body_text = body.get_text(strip=True)
                    print(f"  Body text: {body_text[:300]}")

            except Exception as e:
                print(f"  ERROR: {e}")

        # Also check: does the main page have links to external PDF hosts?
        print("\n\nChecking for external links on main page...")
        for a in all_links:
            href = a["href"]
            text = a.get_text(strip=True)
            if "http" in href and "nkz.ac.jp" not in href:
                print(f"  External: [{text[:40]}] -> {href[:80]}")


main()
