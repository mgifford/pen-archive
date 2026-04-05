import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
import urllib.request
import re

DATA_RAW_DIR = Path(__file__).parent / "data" / "raw"
MANIFEST_FILE = Path(__file__).parent / "manifest.json"

class PenArchiveScraper:
    def __init__(self, start_url: str = "https://www.perc.ca/pen_archives"):
        self.start_url = start_url
        os.makedirs(DATA_RAW_DIR, exist_ok=True)
        
    def scrape(self):
        print(f"Starting scrape of {self.start_url}")
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.start_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for main content to load
            page.wait_for_selector("a")
            
            # Find all links
            links = page.locator("a").all()
            
            for link in links:
                href = link.get_attribute("href")
                text = link.inner_text().strip()
                
                # Check if it's a PDF or we can infer it's an archive edition
                if href and (".pdf" in href.lower() or "attachments/original" in href.lower()):
                    # Simple date extraction heuristic
                    date_match = re.search(r'([A-Za-z]+)\s+(\d{4})|(\d{4})\s+([A-Za-z]+)', text)
                    inferred_date = ""
                    if date_match:
                        inferred_date = " ".join([m for m in date_match.groups() if m])
                    
                    filename = href.split('/')[-1].split('?')[0]
                    if not filename.endswith('.pdf'):
                        filename += '.pdf'
                        
                    results.append({
                        "original_url": href,
                        "link_text": text,
                        "inferred_date": inferred_date,
                        "filename": filename
                    })
                    print(f"Found archive: {text} -> {href}")
            
            browser.close()
        
        self.save_manifest(results)
        return results
        
    def save_manifest(self, results):
        manifest_data = []
        if MANIFEST_FILE.exists():
            with open(MANIFEST_FILE, 'r') as f:
                manifest_data = json.load(f)
                
        # Merge, avoiding duplicates
        existing_urls = {item['original_url'] for item in manifest_data}
        new_items = [r for r in results if r['original_url'] not in existing_urls]
        
        manifest_data.extend(new_items)
        
        with open(MANIFEST_FILE, 'w') as f:
            json.dump(manifest_data, f, indent=2)
            
        print(f"Saved {len(new_items)} new entries to manifest.")

    def download_pdfs(self, limit=5):
        """Helper to download a few for testing."""
        if not MANIFEST_FILE.exists():
            print("No manifest found.")
            return
            
        with open(MANIFEST_FILE, 'r') as f:
            manifest = json.load(f)
            
        downloaded = 0
        for item in manifest:
            if downloaded >= limit:
                break
                
            file_path = DATA_RAW_DIR / item['filename']
            if not file_path.exists():
                print(f"Downloading {item['filename']}...")
                try:
                    # Make sure the href is an absolute URL
                    url = item['original_url']
                    if url.startswith('/'):
                        url = "https://www.perc.ca" + url
                    urllib.request.urlretrieve(url, file_path)
                    print("Success.")
                    downloaded += 1
                except Exception as e:
                    print(f"Failed to download {url}: {e}")
            else:
                print(f"File {item['filename']} already exists.")
