import json
import os
import uuid
import urllib.request
import urllib.parse
import re
from typing import List, Dict, Optional

SITES_FILE = os.path.join(os.path.dirname(__file__), "sites.json")
GDOC_FILE_ID = "1QQ5nj6pgv90nfKKa93L4hpK10lato-7b"

def load_sites() -> List[Dict]:
    if not os.path.exists(SITES_FILE):
        return []
    try:
        with open(SITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def save_sites(sites: List[Dict]) -> bool:
    try:
        with open(SITES_FILE, "w", encoding="utf-8") as f:
            json.dump(sites, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving sites: {e}")
        return False

def extract_name_from_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.replace("www.", "")
        if "reddit.com" in domain:
            return "Reddit (Watchexchange)"
        parts = domain.split(".")
        name = parts[0] if parts else "Website"
        return name.replace("-", " ").title()
    except Exception:
        return "Website"

def clean_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")

def add_site(url: str, name: Optional[str] = None, category: str = "Dealer", custom_search_url: str = "", platform: str = "auto") -> Dict:
    sites = load_sites()
    cleaned_url = clean_url(url)
    if not cleaned_url:
        raise ValueError("Invalid URL provided")
    
    # If already exists, return existing
    for s in sites:
        if clean_url(s.get("url", "")) == cleaned_url:
            return s
            
    site_name = name.strip() if name and name.strip() else extract_name_from_url(cleaned_url)
    new_site = {
        "id": f"site-{str(uuid.uuid4())[:6]}",
        "name": site_name,
        "url": cleaned_url,
        "enabled": True,
        "category": category.strip() or "Dealer",
        "custom_search_url": custom_search_url.strip(),
        "platform": platform or "auto"
    }
    sites.append(new_site)
    save_sites(sites)
    return new_site

def update_site(site_id: str, updates: Dict) -> Optional[Dict]:
    sites = load_sites()
    for s in sites:
        if s["id"] == site_id:
            if "name" in updates and updates["name"]:
                s["name"] = updates["name"].strip()
            if "url" in updates and updates["url"]:
                s["url"] = clean_url(updates["url"])
            if "category" in updates:
                s["category"] = updates["category"].strip() or "Dealer"
            if "enabled" in updates:
                s["enabled"] = bool(updates["enabled"])
            if "custom_search_url" in updates:
                s["custom_search_url"] = updates["custom_search_url"].strip()
            if "platform" in updates:
                s["platform"] = updates["platform"]
            save_sites(sites)
            return s
    return None

def delete_site(site_id: str) -> bool:
    sites = load_sites()
    new_sites = [s for s in sites if s["id"] != site_id]
    if len(new_sites) != len(sites):
        save_sites(new_sites)
        return True
    return False

def toggle_site(site_id: str, enabled: Optional[bool] = None) -> Optional[Dict]:
    sites = load_sites()
    for s in sites:
        if s["id"] == site_id:
            s["enabled"] = not s["enabled"] if enabled is None else enabled
            save_sites(sites)
            return s
    return None

def set_all_sites_enabled(enabled: bool) -> List[Dict]:
    sites = load_sites()
    for s in sites:
        s["enabled"] = enabled
    save_sites(sites)
    return sites

def bulk_import_sites(raw_text: str, category: str = "Dealer") -> List[Dict]:
    lines = raw_text.replace("\r\n", "\n").replace(",", "\n").split("\n")
    added = []
    for line in lines:
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        try:
            name = None
            url = cleaned
            if " - " in cleaned:
                parts = cleaned.split(" - ", 1)
                name, url = parts[0].strip(), parts[1].strip()
            elif " | " in cleaned:
                parts = cleaned.split(" | ", 1)
                name, url = parts[0].strip(), parts[1].strip()
            elif "\t" in cleaned:
                parts = cleaned.split("\t")
                name, url = parts[0].strip(), parts[1].strip()
            elif " : " in cleaned or (": http" in cleaned):
                parts = cleaned.split(":", 1)
                name = parts[0].strip()
                url = ("http:" + parts[1].strip()) if not parts[1].strip().startswith("http") else parts[1].strip()
                
            if "." in url:
                site = add_site(url=url, name=name, category=category)
                added.append(site)
        except Exception as e:
            print(f"Failed to import line '{line}': {e}")
            continue
    return added

def get_raw_sites_text() -> str:
    sites = load_sites()
    lines = []
    for s in sites:
        lines.append(f"{s['url']}")
    return "\n".join(lines)

def set_raw_sites_text(raw_text: str) -> List[Dict]:
    lines = [l.strip() for l in raw_text.replace("\r\n", "\n").split("\n") if l.strip()]
    new_sites = []
    seen = set()
    for idx, line in enumerate(lines):
        clean = clean_url(line)
        if clean and clean not in seen and "." in clean:
            seen.add(clean)
            name = extract_name_from_url(clean)
            new_sites.append({
                "id": f"site-{idx+1:03d}",
                "name": name,
                "url": clean,
                "enabled": True,
                "category": "Forum" if any(f in clean for f in ["forum", "reddit", "timezone", "recon", "patrol"]) else "Dealer",
                "platform": "shopify" if any(s in clean for s in ["lvmwtimepieces", "hodinkee", "vookum", "grandcaliber", "teddybaldassarre", "wolvyn", "mentawatches", "windvintage", "thekeystone", "analogshift"]) else "auto",
                "custom_search_url": ""
            })
    save_sites(new_sites)
    return new_sites

def sync_from_google_drive(file_id: str = GDOC_FILE_ID) -> Dict:
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            urls = re.findall(r'https?://[^\s<>"\',]+', text)
            valid_urls = [u for u in urls if 'google.com' not in u and 'gstatic.com' not in u]
            if valid_urls:
                # Add lvmwtimepieces if not in list
                if not any("lvmwtimepieces" in u for u in valid_urls):
                    valid_urls.insert(0, "https://lvmwtimepieces.com")
                new_sites = set_raw_sites_text("\n".join(valid_urls))
                return {"success": True, "count": len(new_sites), "sites": new_sites}
            return {"success": False, "error": "No valid website URLs found in document"}
    except Exception as e:
        return {"success": False, "error": str(e)}
