import urllib.request
import urllib.parse
import json
import re
import time
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

KNOWN_BRANDS = {
    "cartier", "rolex", "patek", "philippe", "vacheron", "constantin", "lange",
    "sohne", "soehne", "audemars", "piguet", "omega", "tudor", "iwc", "breitling",
    "jaeger", "lecoultre", "richard", "mille", "hublot", "panerai", "zenith",
    "tag", "heuer", "grand", "seiko", "chopard", "bvlgari", "bulgari", "fp",
    "journe", "girard", "perregaux", "blancpain", "breguet", "glashutte"
}

# 60-second in-memory response cache to prevent 429 rate limiting
_SEARCH_CACHE: Dict[str, Any] = {}
_CACHE_EXPIRY: Dict[str, float] = {}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_reference_tokens(query: str) -> List[str]:
    """Extracts non-brand reference / model tokens (e.g. '78086' from 'Cartier 78086')."""
    tokens = re.split(r'[/\\_\- ]+', query.strip())
    ref_tokens = []
    for t in tokens:
        t_clean = t.strip().lower()
        if not t_clean or t_clean in KNOWN_BRANDS:
            continue
        if len(t_clean) >= 3:
            ref_tokens.append(t)
    return ref_tokens

def normalize_watch_query(query: str) -> List[str]:
    """
    Generates intelligent query variations.
    Never falls back to generic brand names (e.g. 'Cartier 78086' -> ['Cartier 78086', '78086']).
    """
    q = query.strip()
    variations = []

    # 1. Cleaned version with spaces
    cleaned_spaces = re.sub(r'[/\\_\-]+', ' ', q).strip()
    if cleaned_spaces:
        variations.append(cleaned_spaces)

    # 2. Extract reference-only tokens (e.g. '78086' from 'Cartier 78086')
    ref_tokens = extract_reference_tokens(q)
    for rt in ref_tokens:
        if rt not in variations:
            variations.append(rt)

    # 3. Base model before slash or hyphen
    if "/" in q:
        slash_p = q.split("/")[0].strip()
        if slash_p and slash_p not in variations and len(slash_p) >= 3:
            variations.append(slash_p)
    if "-" in q:
        hyphen_p = q.split("-")[0].strip()
        if hyphen_p and hyphen_p not in variations and len(hyphen_p) >= 3:
            variations.append(hyphen_p)

    # 4. Original query
    if q not in variations:
        variations.append(q)

    # Filter out generic single brand names from variations
    filtered = []
    for v in variations:
        if v.lower().strip() in KNOWN_BRANDS:
            continue
        filtered.append(v)

    return filtered if filtered else [q]

def calculate_match_score(query: str, title: str, description: str = "", url: str = "") -> float:
    q = query.lower().strip()
    full_text = f"{title} {description} {url}".lower()
    if not q or not full_text:
        return 0.0

    # 1. Required Reference Verification:
    # If the user provided a specific reference number (e.g. '78086' in 'Cartier 78086'),
    # that reference MUST be present in full_text!
    ref_tokens = extract_reference_tokens(query)
    if ref_tokens:
        has_ref_match = False
        for rt in ref_tokens:
            rt_low = rt.lower()
            if rt_low in full_text:
                has_ref_match = True
                break
            if "-" in rt_low and rt_low.split("-")[0] in full_text:
                has_ref_match = True
                break
            if "/" in rt_low and rt_low.split("/")[0] in full_text:
                has_ref_match = True
                break
        if not has_ref_match:
            # Reject false positives that only match the brand name
            return 0.0

    # 2. Exact full query match
    if q in full_text:
        return 1.0

    # 3. Cleaned query (without punctuation) match
    cleaned_q = re.sub(r'[/\\_\-]+', ' ', q).strip()
    if cleaned_q and cleaned_q in full_text:
        return 0.98

    # 4. Variation match
    for v in normalize_watch_query(query):
        v_low = v.lower()
        if len(v_low) >= 4 and v_low in full_text:
            return 0.92

    # 5. Token match
    tokens = [t.lower() for t in re.split(r'[/\\_\- ]+', q) if t]
    matched_tokens = [t for t in tokens if t in full_text]
    if len(matched_tokens) == len(tokens) and len(tokens) > 0:
        return 0.88

    return 0.0

def fetch_url_sync(url: str, timeout: float = 8.0, retries: int = 1) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    for attempt in range(retries + 1):
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
            if e.code == 429 and attempt < retries:
                time.sleep(1.5)
                continue
            return {"status": e.code, "error": str(e), "text": ""}
        except Exception as e:
            return {"status": 0, "error": str(e), "text": ""}
    return {"status": 0, "error": "Max retries exceeded", "text": ""}

def sync_search_site(site: Dict, query: str, timeout: float = 8.0) -> Dict[str, Any]:
    base_url = site["url"].rstrip("/")
    site_id = site.get("id")
    site_name = site.get("name", "Store")
    custom_search_url = site.get("custom_search_url", "")
    
    cache_key = f"{base_url}::{query.strip().lower()}"
    now = time.time()
    if cache_key in _SEARCH_CACHE and _CACHE_EXPIRY.get(cache_key, 0) > now:
        cached_res = dict(_SEARCH_CACHE[cache_key])
        cached_res["query"] = query
        return cached_res

    result_payload = {
        "site_id": site_id,
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

    # 1. Custom Search URL Override
    if custom_search_url:
        formatted_url = custom_search_url.replace("{q}", urllib.parse.quote(query)).replace("{query}", urllib.parse.quote(query))
        prods = scrape_html_search_sync(base_url, formatted_url, query, timeout=timeout)
        if prods:
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            _SEARCH_CACHE[cache_key] = result_payload
            _CACHE_EXPIRY[cache_key] = now + 60.0
            return result_payload

    # 2. Shopify Search (Suggest API & HTML Search)
    for q_term in query_variations:
        prods = search_shopify_sync(base_url, q_term, original_query=query, timeout=timeout)
        if prods:
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            _SEARCH_CACHE[cache_key] = result_payload
            _CACHE_EXPIRY[cache_key] = now + 60.0
            return result_payload

    # 3. General HTML Search Fallbacks
    for q_term in query_variations[:2]:
        encoded_q = urllib.parse.quote(q_term)
        fallback_paths = [
            f"{base_url}/search?q={encoded_q}",
            f"{base_url}/?s={encoded_q}"
        ]
        for path in fallback_paths:
            prods = scrape_html_search_sync(base_url, path, query, timeout=timeout)
            if prods:
                result_payload["products"] = prods
                result_payload["matches_count"] = len(prods)
                _SEARCH_CACHE[cache_key] = result_payload
                _CACHE_EXPIRY[cache_key] = now + 60.0
                return result_payload

    _SEARCH_CACHE[cache_key] = result_payload
    _CACHE_EXPIRY[cache_key] = now + 60.0
    return result_payload

def search_shopify_sync(base_url: str, query: str, original_query: str = "", timeout: float = 8.0) -> List[Dict]:
    target_q = original_query or query
    clean_param = re.sub(r'[/\\_]+', ' ', query).strip()
    encoded_q = urllib.parse.quote(clean_param)

    # Method 1: Clean suggest.json
    suggest_url = f"{base_url}/search/suggest.json?q={encoded_q}&resources[type]=product"
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
                if score >= 0.70:
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
    html_url = f"{base_url}/search?q={encoded_q}&type=product&options%5Bprefix%5D=last"
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

        if score >= 0.70:
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
