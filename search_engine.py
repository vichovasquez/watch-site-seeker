import urllib.request
import urllib.parse
import json
import re
import time
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=64)

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


# --- CURRENCY CONVERSION & TRANSLATION ENGINE ---
EXCHANGE_RATES = {
    "JPY": 0.0068,  # 1 JPY = $0.0068 USD (~147 JPY/USD)
    "EUR": 1.08,    # 1 EUR = $1.08 USD
    "GBP": 1.30,    # 1 GBP = $1.30 USD
    "CHF": 1.15,    # 1 CHF = $1.15 USD
    "CAD": 0.74,    # 1 CAD = $0.74 USD
    "AUD": 0.66     # 1 AUD = $0.66 USD
}

TRANSLATION_MAP = [
    # Japanese Brands & Models
    (r'ロレックス', 'Rolex'),
    (r'パテック\s*フィリップ', 'Patek Philippe'),
    (r'オーデマ\s*ピゲ', 'Audemars Piguet'),
    (r'オメガ', 'Omega'),
    (r'カルティエ', 'Cartier'),
    (r'ヴァシュロン\s*コンスタンタン', 'Vacheron Constantin'),
    (r'ランゲ\s*＆\s*ゾーネ|ランゲ\s*アンド\s*ゾーネ', 'A. Lange & Söhne'),
    (r'チューダー', 'Tudor'),
    (r'グランドセイコー', 'Grand Seiko'),
    (r'デイトナ', 'Daytona'),
    (r'サブマリーナー|サブマリーナ', 'Submariner'),
    (r'GMTマスター', 'GMT-Master'),
    (r'エクスプローラー', 'Explorer'),
    (r'デイデイト', 'Day-Date'),
    (r'デイトジャスト', 'Datejust'),
    (r'スピードマスター', 'Speedmaster'),
    (r'シーマスター', 'Seamaster'),
    (r'ノーチラス', 'Nautilus'),
    (r'アクアノート', 'Aquanaut'),
    (r'カラトラバ', 'Calatrava'),
    (r'ワールドタイム', 'World Time'),
    (r'ロイヤルオーク', 'Royal Oak'),
    (r'タンク', 'Tank'),
    (r'サントス', 'Santos'),
    
    # Japanese Watch Terms
    # Extended Japanese Watch Models & Terms
    (r'チェリーニ', 'Cellini'),
    (r'オイスター\s*パーペチュアル\s*デイト', 'Oyster Perpetual Date'),
    (r'オイスター\s*パーペチュアル', 'Oyster Perpetual'),
    (r'オイスター\s*デイト', 'Oysterdate'),
    (r'スピードキング', 'Speedking'),
    (r'サンダーバード', 'Thunderbird (Turn-O-Graph)'),
    (r'コンビ', 'Two-Tone (Steel & Gold)'),
    (r'ブレス(?:レット)?', 'Bracelet'),
    (r'ダイヤル', 'Dial'),
    (r'ベゼル', 'Bezel'),
    (r'タペストリー', 'Tapestry'),
    (r'シェル', 'Mother of Pearl'),
    (r'リベットブレス', 'Rivet Bracelet'),
    (r'ジュビリーブレス', 'Jubilee Bracelet'),
    (r'オイスターブレス', 'Oyster Bracelet'),
    (r'尾錠', 'Buckle / Clasp'),
    (r'ギャラ(?:ンティ)?(?:カード)?|ギャラ付', 'with Guarantee Card / Papers'),
    (r'冊子', 'Booklet'),
    (r'タグ', 'Hang Tag'),
    (r'ボーイズサイズ|ボーイズ', "Midsize / Boy's"),
    (r'ノンデイト', 'No-Date'),
    (r'オールトリチウム', 'All Tritium'),
    (r'サービスダイヤル', 'Service Dial'),
    (r'国際サービス', 'International Service'),
    (r'修理', 'Service / Repair'),
    (r'明細', 'Receipt / Invoice'),
    (r'ケース', 'Case'),
    (r'バイセロイケース', 'Viceroy Case'),
    (r'クロノメーター', 'Chronometer'),
    (r'クロノグラフ', 'Chronograph'),
    (r'手巻(?:き)?', 'Manual Wind'),
    (r'自動巻(?:き)?', 'Automatic'),
    (r'クォーツ|クオーツ', 'Quartz'),
    (r'メンズ', "Men's"),
    (r'レディース', "Women's"),
    (r'ユニセックス', 'Unisex'),
    (r'箱[・\s]*保(?:証書)?あり|箱[・\s]*保(?:証書)?|箱あり|箱・保証書', 'Box & Papers'),
    (r'保証書あり|保証書', 'Papers / Warranty'),
    (r'箱', 'Box'),
    (r'未使用品|新品', 'Brand New / Unworn'),
    (r'中古品|中古', 'Pre-Owned'),
    (r'極美品|美品', 'Excellent Condition'),
    (r'18金無垢|18金', '18K Gold'),
    (r'14金無垢|14金', '14K Gold'),
    (r'金無垢', 'Solid Gold'),
    (r'ピンクゴールド', 'Rose Gold'),
    (r'ローズゴールド', 'Rose Gold'),
    (r'イエローゴールド', 'Yellow Gold'),
    (r'ホワイトゴールド', 'White Gold'),
    (r'プラチナ', 'Platinum'),
    (r'ステンレス(?:スチール)?', 'Stainless Steel'),
    (r'ブラック文字盤|黒文字盤|黒文字ばん', 'Black Dial'),
    (r'ホワイト文字盤|白文字盤', 'White Dial'),
    (r'ブルー文字盤|青文字盤', 'Blue Dial'),
    (r'シルバー文字盤|銀文字盤', 'Silver Dial'),
    (r'緑文字盤|グリーン文字盤', 'Green Dial'),
    (r'文字盤', 'Dial'),
    (r'年製', ' Year'),
    (r'税込', 'Incl. Tax'),
    (r'税抜', 'Excl. Tax'),
    (r'送料無料', 'Free Shipping'),
    
    # German Terms
    (r'\bHerrenuhr\b', "Men's Watch"),
    (r'\bDamenuhr\b', "Women's Watch"),
    (r'\bArmbanduhr\b', 'Wristwatch'),
    (r'\bAutomatik\b', 'Automatic'),
    (r'\bHandaufzug\b', 'Manual Wind'),
    (r'\bStahl\b', 'Steel'),
    (r'\bEdelstahl\b', 'Stainless Steel'),
    (r'\bGelbgold\b', 'Yellow Gold'),
    (r'\bWeissgold\b|\bWeißgold\b', 'White Gold'),
    (r'\bRoségold\b|\bRotgold\b', 'Rose Gold'),
    (r'\bPlatin\b', 'Platinum'),
    (r'\bLederband\b', 'Leather Strap'),
    (r'\bStahlband\b', 'Steel Bracelet'),
    (r'\bBox und Papiere\b', 'Box & Papers'),
    (r'\bmit Box\b', 'with Box'),
    (r'\bmit Papieren\b', 'with Papers'),
    (r'\bSehr gut\b', 'Very Good Condition'),
    (r'\bUngetragen\b', 'Unworn / Mint'),
    (r'\bZifferblatt\b', 'Dial'),
    (r'\bSchwarz\b', 'Black'),
    (r'\bWeiss\b|\bWeiß\b', 'White'),
    (r'\bBlau\b', 'Blue'),
    (r'\bSilber\b', 'Silver'),
    (r'\bGrün\b', 'Green'),
    (r'\bVerkauft\b', 'Sold')
]

def convert_currency_to_usd(price_str: str) -> str:
    """Converts foreign currencies to USD while preserving the original price in parentheses."""
    if not price_str or price_str == "Inquire" or "inquire" in price_str.lower():
        return "Inquire"
    
    clean_p = price_str.strip()
    if "USD (" in clean_p:
        return clean_p
    
    # 1. Japanese Yen (¥ or ￥ or 円)
    if any(sym in clean_p for sym in ["¥", "￥", "円"]):
        digits = re.sub(r'[^\d]', '', clean_p)
        if digits:
            val = int(digits)
            usd = int(round(val * EXCHANGE_RATES["JPY"]))
            return f"${usd:,} USD ({clean_p})"
            
    # 2. Euros (€)
    if "€" in clean_p or "eur" in clean_p.lower():
        num_str = re.sub(r'[^\d,\.]', '', clean_p)
        num_str = num_str.replace('.', '').replace(',', '.') if (',' in num_str and '.' in num_str) or (',' in num_str and len(num_str.split(',')[-1]) == 2) else num_str.replace(',', '')
        try:
            val = float(num_str)
            usd = int(round(val * EXCHANGE_RATES["EUR"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    # 3. British Pounds (£)
    if "£" in clean_p or "gbp" in clean_p.lower():
        num_str = re.sub(r'[^\d\.]', '', clean_p.replace(',', ''))
        try:
            val = float(num_str)
            usd = int(round(val * EXCHANGE_RATES["GBP"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    # 4. Swiss Francs (CHF)
    if "chf" in clean_p.lower():
        num_str = re.sub(r'[^\d\.]', '', clean_p.replace(',', '').replace("'", ""))
        try:
            val = float(num_str)
            usd = int(round(val * EXCHANGE_RATES["CHF"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    return clean_p

def translate_to_english(text: str) -> str:
    """Translates foreign titles and watch terminology into clean English."""
    if not text:
        return ""
    t = text
    for pattern, repl in TRANSLATION_MAP:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t


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
    title_clean = title.lower().strip()
    clean_url_path = url.split("?")[0].lower() if url else ""
    
    if not title_clean or len(title_clean) < 4:
        return 0.0
    if any(nav in title_clean for nav in ["back to", "search results", "brand selection", "all watches", "open internal link", "current window"]):
        return 0.0
        
    primary_text = f"{title_clean} {clean_url_path}"
    
    # 1. Brand Consistency Validation
    query_brands = extract_query_brands(query)
    if query_brands:
        for opposing_brand, syns in KNOWN_BRANDS.items():
            if opposing_brand not in query_brands:
                if any(re.search(r'\b' + re.escape(syn) + r'\b', primary_text) for syn in syns):
                    has_target_brand = any(any(re.search(r'\b' + re.escape(ts) + r'\b', primary_text) for ts in KNOWN_BRANDS.get(qb, [])) for qb in query_brands)
                    if not has_target_brand:
                        return 0.0

    # 2. Strict Reference Boundary Verification
    ref_tokens = extract_reference_tokens(query)
    if ref_tokens:
        has_ref_match = False
        for rt in ref_tokens:
            rt_low = rt.lower()
            if rt_low.isdigit():
                pattern = r'(?<!\d)' + re.escape(rt_low) + r'(?!\d)'
                if re.search(pattern, primary_text):
                    has_ref_match = True
                    break
            else:
                pattern = r'\b' + re.escape(rt_low) + r'\b'
                if re.search(pattern, primary_text) or rt_low in clean_url_path:
                    has_ref_match = True
                    break
                if "-" in rt_low and rt_low.split("-")[0] in primary_text:
                    has_ref_match = True
                    break
                if "/" in rt_low and rt_low.split("/")[0] in primary_text:
                    has_ref_match = True
                    break
                if "." in rt_low and rt_low.replace(".", "-") in primary_text:
                    has_ref_match = True
                    break
                if "." in rt_low and rt_low.replace(".", " ") in primary_text:
                    has_ref_match = True
                    break
                if "." in rt_low and rt_low.replace(".", "") in primary_text:
                    has_ref_match = True
                    break
        if not has_ref_match:
            return 0.0

    if q in primary_text:
        return 1.0

    cleaned_q = re.sub(r'[/\\_\-\.]+', ' ', q).strip()
    if cleaned_q and cleaned_q in primary_text:
        return 0.98

    for rt in ref_tokens:
        rt_low = rt.lower()
        if rt_low.isdigit():
            if re.search(r'(?<!\d)' + re.escape(rt_low) + r'(?!\d)', primary_text):
                return 0.95
        else:
            if rt_low in primary_text or rt_low in clean_url_path:
                return 0.95

    return 0.0

def fetch_url_sync(url: str, timeout: float = 6.0, retries: int = 2) -> Dict[str, Any]:
    """Synchronously fetches a URL with retries, adaptive 429 backoff, and modern browser headers."""
    last_err = None
    for attempt in range(retries):
        try:
            headers = dict(DEFAULT_HEADERS)
            # Add site-specific referer
            parsed = urllib.parse.urlparse(url)
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
            if "suggest.json" in url or "json" in url:
                headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
                headers["X-Requested-With"] = "XMLHttpRequest"
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                content = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = content.decode(charset, errors="ignore")
                c_type = resp.headers.get("Content-Type", "").lower()
                return {"status": status, "text": text, "url": resp.url, "content_type": c_type}
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                # Exponential backoff on rate limit
                time.sleep(0.6 * (attempt + 1))
            elif e.code in (403, 404, 500):
                break
        except Exception as e:
            last_err = e
            time.sleep(0.2)
    return {"status": getattr(last_err, "code", 0), "text": "", "error": str(last_err)}

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

def scrape_html_search_sync(base_url: str, search_url: str, query: str, timeout: float = 6.0) -> List[Dict]:
    resp = fetch_url_sync(search_url, timeout=timeout)
    if resp.get("status") != 200 or not resp.get("text"):
        return []
    
    html = resp["text"]
    soup = BeautifulSoup(html, "html.parser")
    products = []
    
    # 1. Specialized Parser for WatchRecon
    if "watchrecon.com" in base_url:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title_text = a.get_text(" ", strip=True)
            p_url = urllib.parse.urljoin(base_url, href)
            trans_title = translate_to_english(title_text)
            score = calculate_match_score(query, trans_title, "", p_url)
            if score >= 0.70 and len(title_text) > 10:
                price_match = re.search(r'\$[\d,]+', title_text)
                price = convert_currency_to_usd(price_match.group(0)) if price_match else "Inquire"
                if not any(p["url"] == p_url for p in products):
                    products.append({
                        "title": trans_title[:120],
                        "url": p_url,
                        "price": price,
                        "image": "",
                        "score": round(score, 2)
                    })
        return products[:15]

    # 2. General / Japanese / Custom Dealer Extraction
    card_selectors = [
        ".product-card", ".product-item", ".grid-product", ".item-box", 
        ".goods_item", ".c-card", ".p-item", ".item", ".c-productCard",
        ".card", "article", ".product", "[data-product-id]"
    ]
    
    items = []
    for sel in card_selectors:
        found = soup.select(sel)
        if len(found) >= 2:
            items = found
            break
            
    if not items:
        items = soup.find_all(["div", "li", "article"], class_=re.compile(r'product|item|goods|listing|card', re.I))

    for item in items[:40]:
        text = item.get_text(" ", strip=True)
        
        a_tag = item.find("a", href=True)
        if not a_tag:
            continue
            
        href = a_tag["href"]
        if not href or href.startswith("javascript:") or href == "#":
            continue
        p_url = urllib.parse.urljoin(base_url, href)
        
        title = ""
        for heading in item.find_all(["h2", "h3", "h4", "h5", "a"]):
            h_text = heading.get_text(strip=True)
            if len(h_text) > 8:
                title = h_text
                break
        if not title:
            title = a_tag.get("title") or a_tag.get_text(strip=True)
            
        if not title or len(title) < 5 or "add to cart" in title.lower():
            continue
            
        title = re.sub(r'\s+', ' ', title).strip()
        trans_title = translate_to_english(title)
        
        # Strict Relevance Scoring Gate
        score = calculate_match_score(query, trans_title, text, p_url)
        if score < 0.70:
            continue
        
        # Price extraction (USD, EUR, GBP, JPY ¥ / 円)
        price = "Inquire"
        price_match = re.search(r'(\$|€|£|¥|￥)\s?[\d,]+(?:\.\d{2})?|([\d,]+)\s?円', text + ' ' + title)
        if price_match:
            price = convert_currency_to_usd(price_match.group(0).strip())
            
        # Image extraction
        img_url = ""
        img = item.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy") or img.get("srcset", "").split(",")[0].split(" ")[0]
            if src and not src.startswith("data:"):
                img_url = urllib.parse.urljoin(base_url, src)
                
        if not any(p["url"] == p_url for p in products):
            products.append({
                "title": trans_title[:140],
                "url": p_url,
                "price": price,
                "image": img_url,
                "score": round(score, 2)
            })
            
    # Fallback to direct anchor links if no structured cards found
    if not products:
        for a in soup.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            if len(txt) > 10:
                p_url = urllib.parse.urljoin(base_url, a["href"])
                if any(ext in p_url.lower() for ext in [".html", "/item", "/goods", "/product", "/shop", "/watch"]):
                    trans_txt = translate_to_english(txt)
                    score = calculate_match_score(query, trans_txt, "", p_url)
                    if score >= 0.70:
                        price_match = re.search(r'(\$|€|£|¥|￥)\s?[\d,]+|([\d,]+)\s?円', txt)
                        price = convert_currency_to_usd(price_match.group(0).strip()) if price_match else "Inquire"
                        if not any(p["url"] == p_url for p in products):
                            products.append({
                                "title": trans_txt[:140],
                                "url": p_url,
                                "price": price,
                                "image": "",
                                "score": round(score, 2)
                            })
                        
    return products[:15]

class MultiSiteSearcher:
    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout
        self.executor = SEARCH_EXECUTOR

    async def search_site(self, site: Dict, query: str) -> Dict[str, Any]:
        """Runs search for a single site in a dedicated high-concurrency worker thread."""
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self.executor, sync_search_site, site, query, self.timeout)
        except Exception as e:
            return {
                "site_id": site.get("id"),
                "site_name": site.get("name"),
                "site_url": site.get("url"),
                "status": "error",
                "matches_count": 0,
                "products": [],
                "error": str(e)
            }

    async def search_all(self, sites: List[Dict], query: str, max_total_wait: float = 8.0) -> List[Dict[str, Any]]:
        """Searches all enabled sites concurrently with a strict deadline guarantee."""
        enabled_sites = [s for s in sites if s.get("enabled", True)]
        if not enabled_sites:
            return []
            
        loop = asyncio.get_running_loop()
        futures = [
            loop.run_in_executor(self.executor, sync_search_site, site, query, self.timeout)
            for site in enabled_sites
        ]
        
        done, pending = await asyncio.wait(futures, timeout=max_total_wait)
        for f in pending:
            f.cancel()
            
        results = []
        for f in done:
            try:
                res = f.result()
                if isinstance(res, dict):
                    results.append(res)
            except Exception:
                pass
                
        return results