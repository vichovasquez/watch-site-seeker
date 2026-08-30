import json
import os
from typing import List

REFERENCES_FILE = os.path.join(os.path.dirname(__file__), "references.json")

DEFAULT_REFERENCES = [
    "126518LN-0004",
    "4200H/222A-B934",
    "Cartier 78086",
    "405.035",
    "5231G-001"
]

def load_references() -> List[str]:
    if not os.path.exists(REFERENCES_FILE):
        save_references(DEFAULT_REFERENCES)
        return DEFAULT_REFERENCES
    try:
        with open(REFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) and len(data) > 0 else DEFAULT_REFERENCES
    except Exception:
        return DEFAULT_REFERENCES

def save_references(references: List[str]) -> bool:
    try:
        cleaned = []
        seen = set()
        for r in references:
            item = r.strip()
            if item and item not in seen:
                seen.add(item)
                cleaned.append(item)
        with open(REFERENCES_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving references: {e}")
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
