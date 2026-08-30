import urllib.request
import urllib.parse
import json
import re
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_watch_query(query: str) -> List[str]:
    """Generates query variations (e.g. 126518LN-0004 -> ['126518LN-0004', '126518LN 0004', '126518LN'])."""
    q = query.strip()
    variations = [q]
    if "-" in q:
        variations.append(q.replace("-", " "))
        parts = q.split("-")
        if len(parts) >= 2 and len(parts[0]) >= 4:
            variations.append(parts[0])
    if "/" in q:
        parts = q.split("/")
        if parts[0] not in variations:
            variations.append(parts[0])
    return variations

def calculate_match_score(query: str, title: str, description: str = "", url: str = "") -> float:
    q = query.lower().strip()
    full_text = f"{title} {description} {url}".lower()
    if not q or not full_text:
        return 0.0
    if q in full_text:
        return 1.0
    for v in normalize_watch_query(query)[1:]:
        if v.lower() in full_text:
            return 0.90
    tokens = q.replace("-", " ").replace("/", " ").split()
    matched_tokens = [t for t in tokens if t in full_text]
    if len(matched_tokens) == len(tokens) and len(tokens) > 0:
        return 0.85
    return len(matched_tokens) / len(tokens) if tokens else 0.0

def fetch_url_sync(url: str, headers: Optional[Dict] = None, timeout: float = 8.0) -> Dict[str, Any]:
    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("content-type", "")
            data = resp.read()
            text = data.decode("utf-8", errors="ignore")
            return {
                "status": resp.status,
                "content_type": content_type,
                "text": text,
                "url": resp.url
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": str(e), "text": ""}
    except Exception as e:
        return {"status": 0, "error": str(e), "text": ""}

def sync_search_site(site: Dict, query: str, timeout: float = 8.0) -> Dict[str, Any]:
    base_url = site["url"].rstrip("/")
    platform = site.get("platform", "auto")
    custom_search_url = site.get("custom_search_url", "")
    site_name = site.get("name", "Store")
    
    result_payload = {
        "site_id": site.get("id"),
        "site_name": site_name,
        "site_url": base_url,
        "category": site.get("category", "Dealer"),
        "query": query,
        "status": "success",
        "matches_count": 0,
        "products": [],
        "error": None
    }
    
    query_variations = normalize_watch_query(query)
    
    # Override: Custom Search URL
    if custom_search_url:
        formatted_url = custom_search_url.replace("{q}", urllib.parse.quote(query)).replace("{query}", urllib.parse.quote(query))
        prods = scrape_html_search_sync(base_url, formatted_url, query, timeout=timeout)
        if prods:
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            return result_payload

    # 1. Shopify Search (Suggest API & HTML Search)
    for q_term in query_variations:
        prods = search_shopify_sync(base_url, q_term, original_query=query, timeout=timeout)
        if prods:
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            return result_payload

    # 2. General HTML Search Fallbacks
    fallback_paths = [
        f"{base_url}/search?q={urllib.parse.quote(query)}",
        f"{base_url}/?s={urllib.parse.quote(query)}"
    ]
    for path in fallback_paths:
        prods = scrape_html_search_sync(base_url, path, query, timeout=timeout)
        if prods:
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            return result_payload

    return result_payload

def search_shopify_sync(base_url: str, query: str, original_query: str = "", timeout: float = 8.0) -> List[Dict]:
    target_q = original_query or query
    
    # Method 1: Clean suggest.json
    suggest_url = f"{base_url}/search/suggest.json?q={urllib.parse.quote(query)}&resources[type]=product"
    resp = fetch_url_sync(suggest_url, timeout=timeout)
    if resp.get("status") == 200 and "json" in resp.get("content_type", ""):
        try:
            data = json.loads(resp["text"])
            raw_prods = data.get("resources", {}).get("results", {}).get("products", [])
            products = []
            for p in raw_prods:
                title = p.get("title", "")
                url_suffix = p.get("url", "")
                product_url = urllib.parse.urljoin(base_url, url_suffix) if url_suffix else base_url
                price_val = p.get("price")
                price_str = f"${float(price_val):,.2f}" if price_val else "Inquire"
                img = p.get("image", "") or p.get("featured_image", {}).get("url", "")
                if img and img.startswith("//"):
                    img = "https:" + img
                score = calculate_match_score(target_q, title, p.get("body", ""), product_url)
                if score >= 0.35:
                    products.append({
                        "title": title,
                        "price": price_str,
                        "url": product_url,
                        "image": img,
                        "vendor": p.get("vendor", ""),
                        "score": round(score, 2),
                        "source": "Shopify API"
                    })
            if products:
                return products
        except Exception:
            pass

    # Method 2: HTML search page
    html_url = f"{base_url}/search?q={urllib.parse.quote(query)}&type=product&options%5Bprefix%5D=last"
    return scrape_html_search_sync(base_url, html_url, target_q, timeout=timeout)

def scrape_html_search_sync(base_url: str, search_url: str, query: str, timeout: float = 8.0) -> List[Dict]:
    resp = fetch_url_sync(search_url, timeout=timeout)
    if resp.get("status") != 200 or not resp.get("text"):
        return []
        
    soup = BeautifulSoup(resp["text"], "html.parser")
    links = soup.find_all("a", href=re.compile(r'/products/|/product/|/watch/|/watches/|/item/'))
    seen = set()
    products = []
    
    for a in links:
        href = a["href"]
        clean_href = href.split("?")[0]
        if clean_href in seen:
            continue
            
        title = clean_text(a.get_text())
        if not title or len(title) < 4 or title.lower() in ("clear", "reset", "remove all", "view all"):
            parent = a.find_parent(["div", "li", "article", "h3", "h2"])
            if parent:
                title = clean_text(parent.get_text())
                
        if len(title) < 4:
            continue
            
        product_url = urllib.parse.urljoin(base_url, href)
        score = calculate_match_score(query, title, "", product_url)
        
        if score >= 0.35:
            seen.add(clean_href)
            card = a.find_parent(["li", "div", "article"])
            price_str = "Inquire"
            img_url = ""
            if card:
                price_elem = card.select_one(".price, .price__regular, .money, .amount, .product-price")
                if price_elem:
                    price_str = re.sub(r"\s+", " ", clean_text(price_elem.get_text()))
                img_elem = card.find("img")
                if img_elem:
                    img_url = img_elem.get("src") or img_elem.get("data-src") or ""
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                        
            products.append({
                "title": title,
                "price": price_str,
                "url": product_url,
                "image": img_url,
                "vendor": "",
                "score": round(score, 2),
                "source": "HTML Scrape"
            })
            if len(products) >= 20:
                break
                
    return products

class MultiSiteSearcher:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def search_site(self, site: Dict, query: str) -> Dict[str, Any]:
        """Runs search for a single site in a dedicated async thread."""
        return await asyncio.to_thread(sync_search_site, site, query, self.timeout)

    async def search_all(self, sites: List[Dict], query: str) -> List[Dict[str, Any]]:
        """Searches all enabled sites concurrently in parallel threads."""
        enabled_sites = [s for s in sites if s.get("enabled", True)]
        tasks = [self.search_site(site, query) for site in enabled_sites]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
