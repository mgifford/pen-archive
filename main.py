import argparse
import os
from pathlib import Path
from scraper import PenArchiveScraper
from harness import DigitalArchivistHarness, MockMarkerExtractor, MockTesseractExtractor, Judge
from processors import OllamaProcessor

DATA_PROCESSED_DIR = Path(__file__).parent / "data" / "processed"

def main():
    parser = argparse.ArgumentParser(description="Inference Engineering Harness for PEN Archives")
    parser.add_argument("--scrape", action="store_true", help="Run the Playwright scraper")
    parser.add_argument("--process", action="store_true", help="Process downloaded PDFs")
    parser.add_argument("--limit", type=int, default=1, help="Limit number of files to process")
    
    args = parser.parse_args()
    
    scraper = PenArchiveScraper()
    
    if args.scrape:
        print("Scraping for archive links...")
        scraper.scrape()
        print("Downloading raw PDFs...")
        scraper.download_pdfs(limit=args.limit)
        
    if args.process:
        print(f"Processing up to {args.limit} files from manifest...")
        manifest_path = Path("manifest.json")
        if not manifest_path.exists():
            print("manifest.json not found. Run --scrape first.")
            return
            
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            
        os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
            
        # Instantiate harness components
        extractors = {
            "marker": MockMarkerExtractor(),
            "tesseract": MockTesseractExtractor()
        }
        judge = Judge(model_name="phi3") # As requested, phi3 for judge
        processor = OllamaProcessor(model_name="phi3") # Switched to phi3 to optimize for Frugal AI (smaller model)
        
        harness = DigitalArchivistHarness(extractors=extractors, judge=judge, processor=processor)
        
        processed = 0
        for item in manifest:
            if processed >= args.limit:
                break
                
            pdf_filename = item['filename']
            pdf_path = Path("data") / "raw" / pdf_filename
            
            if not pdf_path.exists():
                continue
                
            # Run pipeline
            final_markdown = harness.run_pipeline(str(pdf_path), item)
            
            # Save output
            output_name = pdf_filename.replace('.pdf', '.md')
            output_path = DATA_PROCESSED_DIR / output_name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
                
            print(f"✅ Saved processed file to {output_path}")
            processed += 1

if __name__ == "__main__":
    main()
