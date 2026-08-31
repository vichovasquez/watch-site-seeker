import urllib.request
import urllib.parse
import json
import re
import time
import asyncio
import functools
import logging
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Structured Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("watch_finder.engine")

# Parser Engine Detection (lxml is 3x-5x faster than html.parser)
try:
    import lxml
    PARSER_ENGINE = "lxml"
except ImportError:
    PARSER_ENGINE = "html.parser"

logger.info(f"Initialized search engine with HTML Parser: '{PARSER_ENGINE}'")

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

# --- TYPED PYDANTIC MODELS ---
class WatchListing(BaseModel):
    title: str
    price: str = "Inquire"
    url: str
    image: Optional[str] = ""
    site_id: Optional[str] = None
    site_name: Optional[str] = "Dealer"
    site_url: Optional[str] = ""
    vendor: Optional[str] = ""
    score: float = 0.8
    matched_reference: Optional[str] = None
    source: Optional[str] = "Web"

class SiteSearchResult(BaseModel):
    site_id: str
    site_name: str
    site_url: str
    category: str = "Dealer"
    query: str
    status: str = "success"
    matches_count: int = 0
    products: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None

# --- ASYNC CONNECTION POOL SINGLETON ---
_ASYNC_CLIENT: Optional[httpx.AsyncClient] = None

def get_async_client() -> httpx.AsyncClient:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None or _ASYNC_CLIENT.is_closed:
        limits = httpx.Limits(max_keepalive_connections=150, max_connections=250, keepalive_expiry=30.0)
        timeout = httpx.Timeout(connect=3.0, read=4.5, write=4.5, pool=5.0)
        _ASYNC_CLIENT = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers=dict(DEFAULT_HEADERS),
            follow_redirects=True,
            verify=False
        )
    return _ASYNC_CLIENT

async def close_async_client():
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT and not _ASYNC_CLIENT.is_closed:
        await _ASYNC_CLIENT.aclose()
        _ASYNC_CLIENT = None

# --- KNOWN BRANDS & SYNONYMS ---
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
DEALER_LATENCY_STATS: Dict[str, float] = {}

# --- PRE-COMPILED STATIC REGEXES ---
RE_TAGS = re.compile(r"<[^>]+>")
RE_WHITESPACE = re.compile(r"\s+")
RE_SLASH_HYPHEN = re.compile(r'[a-zA-Z0-9]+[/-][a-zA-Z0-9/-]+')
RE_DOTTED = re.compile(r"\b\d{3,4}\.\d{3,4}\b")
RE_MODEL_CODE = re.compile(r"\b(?:\d{4,6}[A-Za-z]{1,4}|[A-Za-z]{1,3}\d{4,6}[A-Za-z]{0,3}|\d{4,6})\b")
RE_PUNCTUATION = re.compile(r'[/\\_\-\.]+')
RE_ALL_PUNCT_SPACE = re.compile(r'[/\\_\-\.\s]+')
RE_PRICE_PATTERNS = re.compile(r'(\$|€|£|¥|￥)\s?[\d,]+(?:\.\d{2})?|([\d,]+)\s?円')
RE_PRICE_WATCHRECON = re.compile(r'\$[\d,]+')

# Translation pre-compiled rules
RAW_TRANSLATIONS = [
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
    (r'ヨットマスター', 'Yacht-Master'),
    (r'ミルガウス', 'Milgauss'),
    (r'シードゥエラー', 'Sea-Dweller'),
    (r'エアキング', 'Air-King'),
    (r'スカイドゥエラー', 'Sky-Dweller'),
    (r'ノーチラス', 'Nautilus'),
    (r'アクアノート', 'Aquanaut'),
    (r'カラトラバ', 'Calatrava'),
    (r'ワールドタイム', 'World Time'),
    (r'ロイヤルオーク', 'Royal Oak'),
    (r'スピードマスター', 'Speedmaster'),
    (r'シーマスター', 'Seamaster'),
    (r'タンク', 'Tank'),
    (r'サントス', 'Santos'),
    (r'レベルソ', 'Reverso'),
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
    (r'未使用品|新品', 'Unworn / Brand New'),
    (r'中古(?:品)?', 'Pre-Owned'),
    (r'極美品|美品', 'Excellent Condition'),
    (r'良品', 'Good Condition'),
    (r'箱\s*保(?:証書)?|箱\s*保証書付|箱・保証書付き', 'Box & Papers'),
    (r'保証書付|保証書あり|保付', 'with Papers / Warranty'),
    (r'箱付|箱あり', 'with Box'),
    (r'自動巻き|自動巻', 'Automatic'),
    (r'手巻き|手巻', 'Manual Wind'),
    (r'クォーツ', 'Quartz'),
    (r'メンズ', "Men's"),
    (r'レディース', "Women's"),
    (r'ユニセックス', 'Unisex'),
    (r'黒文字盤|ブラック文字盤', 'Black Dial'),
    (r'白文字盤|ホワイト文字盤', 'White Dial'),
    (r'青文字盤|ブルー文字盤', 'Blue Dial'),
    (r'銀文字盤|シルバー文字盤', 'Silver Dial'),
    (r'緑文字盤|グリーン文字盤', 'Green Dial'),
    (r'文字盤', 'Dial'),
    (r'ステンレススチール|ステンレス|SS', 'Stainless Steel'),
    (r'イエローゴールド|YG', 'Yellow Gold'),
    (r'ホワイトゴールド|WG', 'White Gold'),
    (r'ピンクゴールド|ローズゴールド|PG|RG', 'Rose Gold'),
    (r'プラチナ|PT', 'Platinum'),
    (r'無垢', 'Solid Gold'),
    (r'年式|年製|年', ' Year '),
    (r'ungetragen', 'Unworn'),
    (r'sehr gut', 'Very Good'),
    (r'gut', 'Good'),
    (r'mit box und papieren', 'Box & Papers'),
    (r'mit box', 'with Box'),
    (r'mit papieren', 'with Papers'),
    (r'weißgold', 'White Gold'),
    (r'gelbgold', 'Yellow Gold'),
    (r'roségold', 'Rose Gold'),
    (r'edelstahl', 'Stainless Steel'),
    (r'automatik', 'Automatic'),
    (r'handaufzug', 'Manual Wind'),
]

COMPILED_TRANSLATIONS = [(re.compile(p, re.IGNORECASE), repl) for p, repl in RAW_TRANSLATIONS]

# --- LRU CACHED DYNAMIC REGEX COMPILERS ---
@functools.lru_cache(maxsize=2048)
def get_digit_boundary_regex(token: str) -> re.Pattern:
    return re.compile(r'(?<!\d)' + re.escape(token) + r'(?!\d)', re.IGNORECASE)

@functools.lru_cache(maxsize=2048)
def get_word_boundary_regex(token: str) -> re.Pattern:
    return re.compile(r'' + re.escape(token) + r'', re.IGNORECASE)

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = RE_TAGS.sub(" ", text)
    return RE_WHITESPACE.sub(" ", text).strip()

# --- CURRENCY CONVERSION & TRANSLATION ENGINE ---
EXCHANGE_RATES = {
    "JPY": 0.0068,  # 1 JPY = $0.0068 USD (~147 JPY/USD)
    "EUR": 1.08,    # 1 EUR = $1.08 USD
    "GBP": 1.30,    # 1 GBP = $1.30 USD
    "CHF": 1.15,    # 1 CHF = $1.15 USD
    "CAD": 0.74,    # 1 CAD = $0.74 USD
    "AUD": 0.66     # 1 AUD = $0.66 USD
}

def convert_currency_to_usd(price_str: str) -> str:
    if not price_str or price_str == "Inquire" or "inquire" in price_str.lower():
        return "Inquire"
    
    clean_p = price_str.strip()
    if "USD (" in clean_p:
        return clean_p
    
    if any(sym in clean_p for sym in ["¥", "￥", "円"]):
        digits = re.sub(r'[^\d]', '', clean_p)
        if digits:
            usd = int(round(int(digits) * EXCHANGE_RATES["JPY"]))
            return f"${usd:,} USD ({clean_p})"
            
    if "€" in clean_p or "eur" in clean_p.lower():
        num_str = re.sub(r'[^\d,\.]', '', clean_p)
        num_str = num_str.replace('.', '').replace(',', '.') if (',' in num_str and '.' in num_str) or (',' in num_str and len(num_str.split(',')[-1]) == 2) else num_str.replace(',', '')
        try:
            usd = int(round(float(num_str) * EXCHANGE_RATES["EUR"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    if "£" in clean_p or "gbp" in clean_p.lower():
        num_str = re.sub(r'[^\d\.]', '', clean_p.replace(',', ''))
        try:
            usd = int(round(float(num_str) * EXCHANGE_RATES["GBP"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    if "chf" in clean_p.lower():
        num_str = re.sub(r'[^\d\.]', '', clean_p.replace(',', '').replace("'", ""))
        try:
            usd = int(round(float(num_str) * EXCHANGE_RATES["CHF"]))
            return f"${usd:,} USD ({clean_p})"
        except ValueError:
            pass

    return clean_p

def translate_to_english(text: str) -> str:
    if not text:
        return ""
    translated = text
    for pattern_re, replacement in COMPILED_TRANSLATIONS:
        translated = pattern_re.sub(replacement, translated)
    return RE_WHITESPACE.sub(" ", translated).strip()

def extract_reference_tokens(query: str) -> List[str]:
    q_clean = query.strip()
    tokens = []
    
    slash_hyphen_match = RE_SLASH_HYPHEN.findall(q_clean)
    for m in slash_hyphen_match:
        tokens.append(m.lower())
        for part in re.split(r'[/-]', m):
            if len(part) >= 3:
                tokens.append(part.lower())
                
    dotted_matches = RE_DOTTED.findall(q_clean)
    for dm in dotted_matches:
        tokens.append(dm)
        tokens.append(dm.replace('.', ' '))
        tokens.append(dm.replace('.', '-'))
        tokens.append(dm.replace('.', ''))

    ref_matches = RE_MODEL_CODE.findall(q_clean)
    for rm in ref_matches:
        if len(rm) >= 3:
            tokens.append(rm.lower())
            pure_digits = re.sub(r'[^0-9]', '', rm)
            if len(pure_digits) >= 4 and pure_digits != rm:
                tokens.append(pure_digits)

    seen = set()
    result = []
    for t in tokens:
        if t not in seen and len(t) >= 3:
            seen.add(t)
            result.append(t)
    return result

def get_best_dealer_query(query: str) -> str:
    q_clean = query.strip()
    tokens = extract_reference_tokens(q_clean)
    if not tokens:
        return q_clean
    
    # Priority 1: Alphanumeric model code without delimiters (e.g. 126518ln, 5231g, 4200h)
    for t in tokens:
        if "/" not in t and "-" not in t and "." not in t and " " not in t and not t.isdigit() and len(t) >= 4:
            return t.upper()
            
    # Priority 2: Dotted reference (e.g. 405.035)
    for t in tokens:
        if "." in t:
            return t.upper()
            
    # Priority 3: Pure digit reference >= 4 chars (e.g. 78086, 5711)
    for t in tokens:
        if "/" not in t and "-" not in t and "." not in t and " " not in t and len(t) >= 4:
            return t.upper()
            
    return tokens[0].upper()

def extract_query_brands(query: str) -> List[str]:
    q_low = query.lower()
    found_brands = []
    
    for brand, synonyms in KNOWN_BRANDS.items():
        if any(get_word_boundary_regex(syn).search(q_low) for syn in synonyms):
            found_brands.append(brand)
            
    if not found_brands:
        for ref_prefix, brand in KNOWN_REF_BRANDS.items():
            if ref_prefix in q_low:
                found_brands.append(brand)
                break
                
    return found_brands

def normalize_watch_query(query: str) -> List[str]:
    q_clean = clean_text(query)
    variations = [q_clean]
    
    tokens = extract_reference_tokens(q_clean)
    for tok in tokens:
        if tok not in variations and tok.lower() != q_clean.lower():
            variations.append(tok)
            
    no_punct = RE_PUNCTUATION.sub(' ', q_clean).strip()
    if no_punct not in variations:
        variations.append(no_punct)
        
    no_space = RE_ALL_PUNCT_SPACE.sub('', q_clean).strip()
    if no_space not in variations:
        variations.append(no_space)
        
    seen = set()
    ordered = []
    for v in variations:
        v_low = v.lower()
        if v_low not in seen and len(v) > 1:
            seen.add(v_low)
            ordered.append(v)
            
    return ordered

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
                if any(get_word_boundary_regex(syn).search(primary_text) for syn in syns):
                    has_target_brand = any(any(get_word_boundary_regex(ts).search(primary_text) for ts in KNOWN_BRANDS.get(qb, [])) for qb in query_brands)
                    if not has_target_brand:
                        return 0.0

    # 2. Strict Reference Boundary Verification
    ref_tokens = extract_reference_tokens(query)
    if ref_tokens:
        has_ref_match = False
        for rt in ref_tokens:
            rt_low = rt.lower()
            if rt_low.isdigit():
                if get_digit_boundary_regex(rt_low).search(primary_text):
                    has_ref_match = True
                    break
            else:
                if get_word_boundary_regex(rt_low).search(primary_text) or rt_low in clean_url_path:
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

    cleaned_q = RE_PUNCTUATION.sub(' ', q).strip()
    if cleaned_q and cleaned_q in primary_text:
        return 0.98

    for rt in ref_tokens:
        rt_low = rt.lower()
        if rt_low.isdigit():
            if get_digit_boundary_regex(rt_low).search(primary_text):
                return 0.95
        else:
            if rt_low in primary_text or rt_low in clean_url_path:
                return 0.95

    return 0.0


# --- HIGH-PERFORMANCE ASYNC NETWORKING LAYER ---

async def fetch_url_async(url: str, timeout: float = 4.5, retries: int = 2) -> Dict[str, Any]:
    client = get_async_client()
    last_err = None
    
    parsed = urllib.parse.urlparse(url)
    custom_headers = {
        "Referer": f"{parsed.scheme}://{parsed.netloc}/"
    }
    if "suggest.json" in url or "json" in url:
        custom_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        custom_headers["X-Requested-With"] = "XMLHttpRequest"
        
    for attempt in range(retries):
        try:
            resp = await client.get(url, headers=custom_headers, timeout=timeout)
            c_type = resp.headers.get("Content-Type", "").lower()
            return {
                "status": resp.status_code,
                "text": resp.text,
                "url": str(resp.url),
                "content_type": c_type
            }
        except httpx.HTTPStatusError as e:
            last_err = e
            if e.response.status_code == 429:
                await asyncio.sleep(0.5 * (attempt + 1))
            elif e.response.status_code in (403, 404, 500):
                break
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.15)
            
    return {"status": getattr(last_err, "status_code", 0) if hasattr(last_err, "status_code") else 0, "text": "", "error": str(last_err)}


async def search_shopify_async(base_url: str, query: str, original_query: str = "", timeout: float = 4.5) -> List[Dict]:
    target_q = original_query or query
    clean_param = re.sub(r'[/\_]+', ' ', query).strip()
    encoded_q = urllib.parse.quote(clean_param)

    # Method 1: Async Suggest API
    suggest_url = f"{base_url}/search/suggest.json?q={encoded_q}&resources[type]=product"
    resp = await fetch_url_async(suggest_url, timeout=timeout)
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
                trans_title = translate_to_english(title)
                score = calculate_match_score(target_q, trans_title, p.get("body", ""), product_url)
                if score >= 0.70:
                    seen_handles.add(handle)
                    products.append({
                        "title": trans_title,
                        "price": convert_currency_to_usd(price_str),
                        "url": product_url,
                        "image": img,
                        "vendor": p.get("vendor", ""),
                        "score": round(score, 2),
                        "source": "Shopify API"
                    })
            if products:
                return products
            return []
        except Exception:
            pass

    # Method 2: HTML Search fallback
    if resp.get("status") in (404, 0) or "json" not in resp.get("content_type", ""):
        html_url = f"{base_url}/search?q={encoded_q}&type=product"
        return await scrape_html_search_async(base_url, html_url, target_q, timeout=timeout)
        
    return []


async def scrape_html_search_async(base_url: str, search_url: str, query: str, timeout: float = 4.5) -> List[Dict]:
    resp = await fetch_url_async(search_url, timeout=timeout)
    if resp.get("status") != 200 or not resp.get("text"):
        return []
    
    html = resp["text"]
    soup = BeautifulSoup(html, PARSER_ENGINE)
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
                price_match = RE_PRICE_WATCHRECON.search(title_text)
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
            
        title = RE_WHITESPACE.sub(' ', title).strip()
        trans_title = translate_to_english(title)
        
        score = calculate_match_score(query, trans_title, text, p_url)
        if score < 0.70:
            continue
        
        # Price extraction (USD, EUR, GBP, JPY ¥ / 円)
        price = "Inquire"
        price_match = RE_PRICE_PATTERNS.search(text + ' ' + title)
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
            
    # Fallback to direct anchor links
    if not products:
        for a in soup.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            if len(txt) > 10:
                p_url = urllib.parse.urljoin(base_url, a["href"])
                if any(ext in p_url.lower() for ext in [".html", "/item", "/goods", "/product", "/shop", "/watch", "/watches"]):
                    trans_txt = translate_to_english(txt)
                    score = calculate_match_score(query, trans_txt, "", p_url)
                    if score >= 0.70:
                        price_match = RE_PRICE_PATTERNS.search(txt)
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


async def async_search_site(site: Dict, query: str, timeout: float = 4.5) -> Dict[str, Any]:
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

    t0 = time.time()
    
    # Best single dealer query term: root reference number without sub-variant suffixes (e.g. '126518LN' from '126518LN-0004')
    dealer_q = get_best_dealer_query(query)

    # 1. Custom Search URL Override
    if custom_search_url:
        formatted_url = custom_search_url.replace("{q}", urllib.parse.quote(dealer_q)).replace("{query}", urllib.parse.quote(dealer_q))
        prods = await scrape_html_search_async(base_url, formatted_url, query, timeout=timeout)
        if prods:
            for p in prods:
                p["site_id"] = site_id
                p["site_name"] = site_name
                p["site_url"] = base_url
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            _SEARCH_CACHE[cache_key] = result_payload
            _CACHE_EXPIRY[cache_key] = now + 180.0
            DEALER_LATENCY_STATS[site_id] = time.time() - t0
            return result_payload

    # 2. Shopify Search (Suggest API & fallback)
    if platform in ("shopify", "auto"):
        prods = await search_shopify_async(base_url, dealer_q, original_query=query, timeout=timeout)
        if prods:
            for p in prods:
                p["site_id"] = site_id
                p["site_name"] = site_name
                p["site_url"] = base_url
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            _SEARCH_CACHE[cache_key] = result_payload
            _CACHE_EXPIRY[cache_key] = now + 180.0
            DEALER_LATENCY_STATS[site_id] = time.time() - t0
            return result_payload

    # 3. General HTML Search Fallback
    encoded_q = urllib.parse.quote(dealer_q)
    fallback_paths = [
        f"{base_url}/search?q={encoded_q}",
        f"{base_url}/?s={encoded_q}"
    ]
    for path in fallback_paths:
        prods = await scrape_html_search_async(base_url, path, query, timeout=timeout)
        if prods:
            for p in prods:
                p["site_id"] = site_id
                p["site_name"] = site_name
                p["site_url"] = base_url
            result_payload["products"] = prods
            result_payload["matches_count"] = len(prods)
            _SEARCH_CACHE[cache_key] = result_payload
            _CACHE_EXPIRY[cache_key] = now + 180.0
            DEALER_LATENCY_STATS[site_id] = time.time() - t0
            return result_payload

    _SEARCH_CACHE[cache_key] = result_payload
    _CACHE_EXPIRY[cache_key] = now + 180.0
    DEALER_LATENCY_STATS[site_id] = time.time() - t0
    return result_payload


class MultiSiteSearcher:
    def __init__(self, timeout: float = 4.5):
        self.timeout = timeout

    async def search_site(self, site: Dict, query: str) -> Dict[str, Any]:
        try:
            return await async_search_site(site, query, self.timeout)
        except Exception as e:
            logger.warning(f"Error searching {site.get('name')}: {e}")
            return {
                "site_id": site.get("id"),
                "site_name": site.get("name"),
                "site_url": site.get("url"),
                "status": "error",
                "matches_count": 0,
                "products": [],
                "error": str(e)
            }

    async def search_all(self, sites: List[Dict], query: str, max_total_wait: float = 5.0) -> List[Dict[str, Any]]:
        enabled_sites = [s for s in sites if s.get("enabled", True)]
        if not enabled_sites:
            return []
            
        tasks = [asyncio.create_task(self.search_site(site, query)) for site in enabled_sites]
        done, pending = await asyncio.wait(tasks, timeout=max_total_wait)
        
        for task in pending:
            task.cancel()
            
        results = []
        for task in done:
            try:
                res = task.result()
                results.append(res)
            except Exception:
                pass
                
        return results
