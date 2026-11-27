"""
Conservative starter scraper for public portal pages.

Use only pages that are publicly accessible and permitted by the portal's
terms/robots rules. This script does not log in, submit forms, solve CAPTCHAs,
or access personal/application records. For JS-heavy pages, inspect manually
with browser DevTools or use the optional Playwright workflow in README.md.
"""
from urllib.parse import urlparse, urljoin
import time
import requests
from bs4 import BeautifulSoup

ALLOWED_HOSTS = {
    "sevasindhu.karnataka.gov.in",
    "sevasindhuservices.karnataka.gov.in",
    "nadakacheri.karnataka.gov.in",
}
HEADERS = {"User-Agent": "DocuGuide student research project (contact: add-project-contact)"}

def fetch_page(url, delay_seconds=2):
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Host not allowlisted: {host}")
    time.sleep(delay_seconds)
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text

def extract_page_info(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    headings = [h.get_text(" ", strip=True) for h in soup.select("h1, h2, h3")]
    links = []
    for anchor in soup.select("a[href]"):
        label = anchor.get_text(" ", strip=True)
        target = urljoin(page_url, anchor["href"])
        if label:
            links.append({"text": label, "url": target})
    text = soup.get_text(" ", strip=True)
    return {"url": page_url, "title": title, "headings": headings,
            "links": links, "visible_text": text}

def scrape_public_page(url):
    html = fetch_page(url)
    return extract_page_info(html, url)

if __name__ == "__main__":
    start_urls = [
        "https://sevasindhu.karnataka.gov.in/",
        "https://nadakacheri.karnataka.gov.in/ajsk",
    ]
    for url in start_urls:
        try:
            page = scrape_public_page(url)
            print("\\nURL:", page["url"])
            print("TITLE:", page["title"])
            print("HEADINGS:", page["headings"][:15])
            print("LINKS:", page["links"][:15])
            print("TEXT PREVIEW:", page["visible_text"][:1200])
        except Exception as error:
            print(f"Could not scrape {url}: {error}")
