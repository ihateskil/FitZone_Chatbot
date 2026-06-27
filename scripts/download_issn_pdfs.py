#!/usr/bin/env python3
"""Download open-access ISSN Position Stands into the knowledge database."""

import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

# Dictionary of open-access Springer Nature PDF links for core ISSN Position Stands
# These are the official publisher PDFs hosted by Springer (BioMed Central).
# Also available on PubMed Central at the respective PMC IDs.
ISSN_STANDS = {
    "ISSN_Protein_and_Exercise.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-017-0177-8.pdf",
    "ISSN_Diets_and_Body_Composition.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-017-0174-y.pdf",
    "ISSN_Nutrient_Timing.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-017-0189-4.pdf",
    "ISSN_Caffeine.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-020-00383-4.pdf",
    "ISSN_Creatine.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-017-0173-z.pdf",
    "ISSN_Beta_Alanine.pdf": "https://link.springer.com/content/pdf/10.1186/s12970-015-0090-y.pdf"
}

def download_pdf(url: str, dest_path: Path):
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    print(f"Downloading {dest_path.name}...")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            data = response.read()
            if data[:4] != b'%PDF':
                print(f"  -> WARNING: Downloaded file is not a PDF (starts with {data[:8]})")
            with open(dest_path, "wb") as f:
                f.write(data)
        print(f"  -> Saved successfully ({len(data)} bytes).")
    except Exception as e:
        print(f"  -> Failed to download: {e}")

def main():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    for filename, url in ISSN_STANDS.items():
        dest_path = KNOWLEDGE_DIR / filename
        download_pdf(url, dest_path)
    print("\nAll ISSN position stands processed.")

if __name__ == "__main__":
    main()
