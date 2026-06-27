#!/usr/bin/env python3
"""Download open-access ISSN Position Stands into the knowledge database."""

import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

# Dictionary of open-access PMC PDF links for core ISSN Position Stands
ISSN_STANDS = {
    "ISSN_Protein_and_Exercise.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5477153/pdf/12970_2017_Article_177.pdf",
    "ISSN_Diets_and_Body_Composition.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5470183/pdf/12970_2017_Article_174.pdf",
    "ISSN_Nutrient_Timing.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5596471/pdf/12970_2017_Article_189.pdf",
    "ISSN_Caffeine.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7777221/pdf/12970_2020_Article_383.pdf",
    "ISSN_Creatine.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5469049/pdf/12970_2017_Article_173.pdf",
    "ISSN_Beta_Alanine.pdf": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4501114/pdf/12970_2015_Article_90.pdf"
}

def download_pdf(url: str, dest_path: Path):
    req = urllib.request.Request(url, headers={'User-Agent': 'FitZone-Research-Bot/1.0'})
    print(f"Downloading {dest_path.name}...")
    try:
        with urllib.request.urlopen(req) as response:
            with open(dest_path, "wb") as f:
                f.write(response.read())
        print(f"  -> Saved successfully.")
    except Exception as e:
        print(f"  -> Failed to download: {e}")

def main():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    for filename, url in ISSN_STANDS.items():
        dest_path = KNOWLEDGE_DIR / filename
        if not dest_path.exists():
            download_pdf(url, dest_path)
        else:
            print(f"Skipping {filename} (already exists)")
            
    print("\nAll ISSN position stands processed.")

if __name__ == "__main__":
    main()
