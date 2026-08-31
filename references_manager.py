import json
import os
import urllib.request
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

REFERENCES_FILE = os.path.join(os.path.dirname(__file__), "references.json")
DEFAULT_GDOC_FILE_ID = "15Jt2CXVU-crP8qJtV6lQ1B58fssOCtgkAvM4M-B_Tdg"

DEFAULT_REFERENCES = [
    "126518LN-0004",
    "4200H/222A-B934",
    "Cartier 78086",
    "Lange 405.035",
    "5231G-001"
]

def load_references() -> List[str]:
    if not os.path.exists(REFERENCES_FILE):
        return DEFAULT_REFERENCES
    try:
        with open(REFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                clean = []
                for item in data:
                    if isinstance(item, str):
                        clean.append(item.strip())
                    elif isinstance(item, dict) and "ref" in item:
                        clean.append(item["ref"].strip())
                return clean
            return DEFAULT_REFERENCES
    except Exception:
        return DEFAULT_REFERENCES

def save_references(references: List[str]) -> bool:
    tmp_file = f"{REFERENCES_FILE}.tmp"
    try:
        cleaned = []
        seen = set()
        for r in references:
            item = r.strip()
            if item and item not in seen:
                seen.add(item)
                cleaned.append(item)
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, REFERENCES_FILE)
        return True
    except Exception as e:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        print(f"Error saving references atomically: {e}")
        return False

def add_reference(ref: str) -> List[str]:
    refs = load_references()
    cleaned = ref.strip()
    if cleaned and cleaned not in refs:
        refs.append(cleaned)
        save_references(refs)
    return refs

def delete_reference(ref: str) -> List[str]:
    refs = load_references()
    cleaned = ref.strip()
    new_refs = [r for r in refs if r != cleaned]
    save_references(new_refs)
    return new_refs

def set_raw_references_text(raw_text: str) -> List[str]:
    lines = [l.strip() for l in raw_text.replace("\r\n", "\n").replace(",", "\n").split("\n") if l.strip()]
    save_references(lines)
    return load_references()

def extract_file_id(url_or_id: Optional[str], default: str) -> str:
    if not url_or_id:
        return default
    m = re.search(r'[\/=]([a-zA-Z0-9_-]{25,})', url_or_id)
    if m:
        return m.group(1)
    if len(url_or_id.strip()) >= 25 and "/" not in url_or_id:
        return url_or_id.strip()
    return default

def sync_references_from_google_doc(doc_url_or_id: Optional[str] = None) -> Dict[str, Any]:
    """Downloads watch references directly from Google Doc."""
    file_id = extract_file_id(doc_url_or_id, DEFAULT_GDOC_FILE_ID)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    }
    html_url = f"https://docs.google.com/document/d/{file_id}/export?format=html"
    try:
        req = urllib.request.Request(html_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            raw_items = [p.get_text().strip() for p in soup.find_all(['p', 'li', 'td', 'span']) if p.get_text().strip()]
            
            unique_refs = []
            seen = set()
            for item in raw_items:
                item_clean = re.sub(r'[\ufeff\u200b\u200e\u200f]', '', item).strip()
                if not item_clean or len(item_clean) < 3 or len(item_clean) > 80:
                    continue
                if item_clean not in seen and not item_clean.lower().startswith(('http', 'google', 'published', 'document')):
                    seen.add(item_clean)
                    unique_refs.append(item_clean)
                    
            if unique_refs:
                save_references(unique_refs)
                return {"success": True, "count": len(unique_refs), "references": unique_refs}
            else:
                save_references(DEFAULT_REFERENCES)
                return {"success": True, "count": len(DEFAULT_REFERENCES), "references": DEFAULT_REFERENCES}
    except Exception as e:
        print(f"Failed to sync references from Google Doc: {e}")
        return {"success": False, "error": str(e), "references": load_references()}
