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
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

KNOWN_BRANDS: Dict[str, List[str]] = {
    "cartier": ["cartier"],
    "rolex": ["rolex"],
    "patek": ["patek", "philippe"],
    "vacheron": ["vacheron", "constantin", "historiques", "overseas"],
    "lange": ["lange", "sohne", "soehne", "datograph", "saxonia", "odysseus", "zeitwerk", "cabaret"],
    "audemars": ["audemars", "piguet", "royal oak", "offshore"],
    "omega": ["omega", "speedmaster", "seamaster", "constellation"],
    "breitling": ["breitling", "navitimer", "superocean", "chronomat"],
    "iwc": ["iwc", "schaffhausen", "portugieser", "portofino"],
    "tudor": ["tudor", "black bay", "pelagos"],
    "richard": ["richard mille"],
    "panerai": ["panerai", "luminor", "radiomir"],
    "zenith": ["zenith", "el primero", "chronomaster"],
    "tag": ["tag heuer", "heuer"],
    "grand": ["grand seiko"],
    "chopard": ["chopard", "mille miglia", "alpine eagle"],
    "bvlgari": ["bvlgari", "bulgari", "octo finissimo"],
    "fp": ["fp journe", "f.p. journe", "journe"],
    "girard": ["girard perregaux", "laureato"],
    "blancpain": ["blancpain", "fifty fathoms"],
    "breguet": ["breguet", "marine", "tradition"],
    "glashutte": ["glashutte original", "glashütte original"]
}

KNOWN_REF_BRANDS = {
    "5231": "patek",
    "5231g": "patek",
    "5711": "patek",
    "5712": "patek",
    "5270": "patek",
    "5167": "patek",
    "126518": "rolex",
    "126518ln": "rolex",
    "116500": "rolex",
    "116520": "rolex",
    "126610": "rolex",
    "4200h": "vacheron",
    "222": "vacheron",
    "4020t": "vacheron",
    "4500v": "vacheron",
    "78086": "cartier",
    "405.035": "lange",
    "405": "lange",
}

_SEARCH_CACHE: Dict[str, Any] = {}
_CACHE_EXPIRY: Dict[str, float] = {}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_reference_tokens(query: str) -> List[str]:
    """
    Extracts non-brand reference / model tokens.
    Handles dots, hyphens, and slashes.
    Ignores pure dial/variant suffixes (e.g. '001', '0004', '010') as standalone tokens.
    """
    tokens = re.split(r'[/\\_\- ]+', query.strip())
    ref_tokens = []
    for t in tokens:
        t_clean = t.strip().lower()
        if not t_clean or any(t_clean == b or t_clean in syns for b, syns in KNOWN_BRANDS.items()):
            continue
        # Avoid treating pure dial/variant suffixes like '001', '010', '0004' as standalone ref tokens
        if re.match(r'^0+\d+$', t_clean):
            continue
        if len(t_clean) >= 3:
            if t_clean not in ref_tokens:
                ref_tokens.append(t_clean)
            if "." in t_clean:
                dot_space = t_clean.replace(".", " ")
                dot_hyphen = t_clean.replace(".", "-")
                dot_num = t_clean.replace(".", "")
                if dot_space not in ref_tokens: ref_tokens.append(dot_space)
                if dot_hyphen not in ref_tokens: ref_tokens.append(dot_hyphen)
                if dot_num not in ref_tokens: ref_tokens.append(dot_num)
            else:
                num_match = re.search(r'\d{3,}', t_clean)
                if num_match:
                    root_num = num_match.group(0)
                    if root_num not in ref_tokens and len(root_num) >= 3:
                        ref_tokens.append(root_num)
    return ref_tokens

def extract_query_brands(query: str) -> List[str]:
    q_low = query.lower()
    brands = []
    for brand, synonyms in KNOWN_BRANDS.items():
        if re.search(r'\b' + re.escape(brand) + r'\b', q_low) or any(re.search(r'\b' + re.escape(s) + r'\b', q_low) for s in synonyms):
            brands.append(brand)
            
    if not brands:
        ref_tokens = extract_reference_tokens(query)
        for rt in ref_tokens:
            rt_clean = rt.lower().replace(".", "").replace("-", "").replace(" ", "")
            for ref_prefix, ref_brand in KNOWN_REF_BRANDS.items():
                if ref_prefix in rt_clean:
                    if ref_brand not in brands:
                        brands.append(ref_brand)
    return brands

def normalize_watch_query(query: str) -> List[str]:
    """
    Generates intelligent query variations for network search.
    """
    q = query.strip()
    variations = []

    # 1. Cleaned version with spaces replacing all punctuation
    cleaned_spaces = re.sub(r'[/\\_\-\.]+', ' ', q).strip()
    if cleaned_spaces:
        variations.append(cleaned_spaces)

    # 2. Extract reference-only tokens
    ref_tokens = extract_reference_tokens(q)
    for rt in ref_tokens:
        if rt not in variations:
            variations.append(rt)

    # 3. Base model before slash, hyphen, or dot
    if "/" in q:
        slash_p = q.split("/")[0].strip()
        if slash_p and slash_p not in variations and len(slash_p) >= 3:
            variations.append(slash_p)
    if "-" in q:
        hyphen_p = q.split("-")[0].strip()
        if hyphen_p and hyphen_p not in variations and len(hyphen_p) >= 3:
            variations.append(hyphen_p)
    if "." in q:
        dot_p = q.split(".")[0].strip()
        if dot_p and dot_p not in variations and len(dot_p) >= 3:
            variations.append(dot_p)

    # 4. Original query
    if q not in variations:
        variations.append(q)

    # Filter out generic single brand names from variations
    filtered = []
    for v in variations:
        v_low = v.lower().strip()
        if any(v_low == b or v_low in syns for b, syns in KNOWN_BRANDS.items()):
            continue
        filtered.append(v)

    return filtered if filtered else [q]

def calculate_match_score(query: str, title: str, description: str = "", url: str = "") -> float:
    q = query.lower().strip()
    clean_url_path = url.split("?")[0].lower() if url else ""
    full_text = f"{title} {description} {clean_url_path}".lower()
    
    if not q or not full_text:
        return 0.0

    # 1. Brand Consistency Validation
    query_brands = extract_query_brands(query)
    if query_brands:
        for opposing_brand, syns in KNOWN_BRANDS.items():
            if opposing_brand not in query_brands:
                if any(re.search(r'\b' + re.escape(syn) + r'\b', full_text) for syn in syns):
                    has_target_brand = any(any(re.search(r'\b' + re.escape(ts) + r'\b', full_text) for ts in KNOWN_BRANDS.get(qb, [])) for qb in query_brands)
                    if not has_target_brand:
                        return 0.0

    # 2. Strict Reference Boundary Verification
    ref_tokens = extract_reference_tokens(query)
    if ref_tokens:
        has_ref_match = False
        for rt in ref_tokens:
            rt_low = rt.lower()
            if rt_low.isdigit():
                # Strict non-digit boundary so '15231' or '52310' does NOT match '5231'
                pattern = r'(?<!\d)' + re.escape(rt_low) + r'(?!\d)'
                if re.search(pattern, full_text):
                    has_ref_match = True
                    break
            else:
                pattern = r'\b' + re.escape(rt_low) + r'\b'
                if re.search(pattern, full_text) or rt_low in clean_url_path:
                    has_ref_match = True
                    break
                if "-" in rt_low and rt_low.split("-")[0] in full_text:
                    has_ref_match = True
                    break
                if "/" in rt_low and rt_low.split("/")[0] in full_text:
                    has_ref_match = True
                    break
                if "." in rt_low and rt_low.replace(".", "-") in full_text:
                    has_ref_match = True
                    break
                if "." in rt_low and rt_low.replace(".", " ") in full_text:
                    has_ref_match = True
                    break
        if not has_ref_match:
            return 0.0

    # Exact full query match
    if q in full_text:
        return 1.0

    # Cleaned query match
    cleaned_q = re.sub(r'[/\\_\-\.]+', ' ', q).strip()
    if cleaned_q and cleaned_q in full_text:
        return 0.98

    # Reference token match
    for rt in ref_tokens:
        rt_low = rt.lower()
        if rt_low.isdigit():
            if re.search(r'(?<!\d)' + re.escape(rt_low) + r'(?!\d)', full_text):
                return 0.95
        else:
            if rt_low in full_text or rt_low in clean_url_path:
                return 0.95

    return 0.0

def fetch_url_sync(url: str, timeout: float = 8.0, retries: int = 2) -> Dict[str, Any]:
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
                backoff = 1.5 * (attempt + 1)
                time.sleep(backoff)
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
    platform = site.get("platform", "auto")
    
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

    # 2. Shopify Search (Suggest API & HTML Search) for all Shopify or Auto sites
    if platform in ("shopify", "auto"):
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
            seen_handles = set()
            for p in raw_prods:
                title = p.get("title", "")
                handle = p.get("handle", "")
                if handle in seen_handles:
                    continue
                url_suffix = p.get("url", "")
                product_url = urllib.parse.urljoin(base_url, url_suffix) if url_suffix else base_url
                price_val = p.get("price")
                price_str = f"${float(price_val):,.2f}" if price_val and float(price_val) > 0 else "Inquire"
                img = p.get("image", "") or p.get("featured_image", {}).get("url", "")
                if img and img.startswith("//"):
                    img = "https:" + img
                score = calculate_match_score(target_q, title, p.get("body", ""), product_url)
                if score >= 0.70:
                    seen_handles.add(handle)
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

from concurrent.futures import ThreadPoolExecutor

SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=64)

class MultiSiteSearcher:
    def __init__(self, timeout: float = 3.5):
        self.timeout = timeout
        self.executor = SEARCH_EXECUTOR

    async def search_site(self, site: Dict, query: str) -> Dict[str, Any]:
        """Runs search for a single site in a dedicated high-concurrency worker thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, sync_search_site, site, query, self.timeout)

    async def search_all(self, sites: List[Dict], query: str) -> List[Dict[str, Any]]:
        """Searches all enabled sites concurrently across 64 high-concurrency worker threads."""
        enabled_sites = [s for s in sites if s.get("enabled", True)]
        tasks = [self.search_site(site, query) for site in enabled_sites]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
