#!/usr/bin/env python3
"""Ingest exercise data from the open-source wger API and convert it for FitZone."""

import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_FILE = BASE_DIR / "knowledge" / "exercises.json"

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)

def strip_tags(html):
    if not html:
        return ""
    s = HTMLStripper()
    s.feed(html)
    return s.get_data().strip()

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'FitZone-Bot/1.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def main():
    print("Fetching exercises from wger exerciseinfo API...")
    exercises = []
    url = "https://wger.de/api/v2/exerciseinfo/?language=2&limit=200" # Language 2 = English
    
    while url:
        print(f"Fetching {url}...")
        data = fetch_json(url)
        exercises.extend(data['results'])
        url = data.get('next')

    print(f"Processing {len(exercises)} exercises...")
    
    fitzone_exercises = []
    for ex in exercises:
        # Find English translation (language = 2)
        eng_trans = next((t for t in ex.get('translations', []) if t.get('language') == 2), None)
        if not eng_trans:
            continue
            
        name = eng_trans.get('name', '').strip()
        if not name:
            continue
            
        desc = strip_tags(eng_trans.get('description', ''))
        
        category = ex.get('category', {}).get('name', 'Unknown')
        primary_muscles = [m.get('name', 'Unknown') for m in ex.get('muscles', [])]
        secondary_muscles = [m.get('name', 'Unknown') for m in ex.get('muscles_secondary', [])]
        equipment = [e.get('name', 'Unknown') for e in ex.get('equipment', [])]
        
        fitzone_exercises.append({
            "name": name,
            "category": category,
            "target_muscles": primary_muscles,
            "synergists": secondary_muscles,
            "equipment": equipment,
            "instructions": desc,
            "cues": []
        })

    # Save to knowledge/exercises.json
    EXERCISES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EXERCISES_FILE, "w", encoding="utf-8") as f:
        json.dump(fitzone_exercises, f, indent=2)
        
    print(f"Successfully saved {len(fitzone_exercises)} exercises to {EXERCISES_FILE}")

if __name__ == "__main__":
    main()
