import logging
import random
import re
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as c_requests
    HAS_CURL = True
except ImportError:
    c_requests = None
    HAS_CURL = False

MARKETPLACE = "www.amazon.it"
CREATORS_API_BASE = "https://creatorsapi.amazon/catalog/v1"
DEFAULT_EU_TOKEN_URL = "https://api.amazon.co.uk/auth/o2/token"
OFFERS_CACHE_TTL_SECONDS = 2 * 60
METADATA_CACHE_TTL_SECONDS = 24 * 60 * 60
VETRINA_CACHE_TTL_SECONDS = 2 * 60
MAX_RESULTS = 50
MAX_CREATORS_PAGES = 5
HTTP_TIMEOUT_SECONDS = 6
RETRY_BACKOFF_SECONDS = 0.35

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Popolarità": "Featured",
    "Recensioni": "AvgCustomerReviews",
}

SORT_FALLBACK_MAP = {
    "Prezzo minimo": "price-asc-rank",
    "Popolarità": "exact-aware-popularity-rank",
    "Recensioni": "review-rank",
    "Numero di vendite": "exact-aware-popularity-rank",
}

RE_ASIN = re.compile(r"(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&#]|$)", re.IGNORECASE)
RE_PRICE = re.compile(r'(\d{1,3}(?:\.\d{3})*|\d+)[,\.](\d{2})')
RE_STAR = re.compile(r'(\d+[.,]\d+)\s*(?:su|out of|di)\s*5', re.IGNORECASE)
RE_DIGITS = re.compile(r'[^\d]')

_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}
_HTTP_SESSION = requests.Session()
_CURL_SESSION = None
if HAS_CURL:
    try:
        _CURL_SESSION = c_requests.Session()
    except Exception:
        HAS_CURL = False
        _CURL_SESSION = None

LOGGER = logging.getLogger("amazon_affiliate")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s amazon_affiliate: %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
]

KEYWORDS_VETRINA = [
    "offerte lampo tecnologia",
    "offerte scarpe sneaker",
    "smartwatch offerte del giorno",
    "cuffie bluetooth offerta",
    "elettrodomestici cucina sconti",
    "accessori smartphone offerte",
    "cura della persona sconti",
    "abbigliamento sportivo offerte",
]


def _amazon_secrets() -> Dict[str, Any]:
    try:
        return dict(st.secrets.get("amazon_api", {}))
    except Exception:
        return {}


def get_partner_tag() -> str:
    return str(_amazon_secrets().get("partner_tag", "")).strip()


def build_affiliate_link(asin: str, partner_tag: Optional[str] = None) -> str:
    asin_clean = (asin or "").strip().upper()
    tag = (partner_tag or get_partner_tag()).strip()
    if len(asin_clean) != 10 or not tag:
        return ""
    safe_tag = urllib.parse.quote(tag, safe="-_.")
    return f"https://www.amazon.it/dp/{asin_clean}?tag={safe_tag}&th=1&psc=1"


def _affiliate_detail_url(item: Dict[str, Any], asin: str, partner_tag: str) -> str:
    raw_url = str(item.get("detailPageURL") or "").strip()
    if not raw_url:
        return build_affiliate_link(asin, partner_tag)
    try:
        parsed = urllib.parse.urlsplit(raw_url)
        if not parsed.netloc.lower().endswith("amazon.it"):
            return build_affiliate_link(asin, partner_tag)
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if k.lower() != "tag"]
        query.insert(0, ("tag", partner_tag))
        normalized = urllib.parse.urlunsplit((
            "https", parsed.netloc, parsed.path, urllib.parse.urlencode(query), ""
        ))
        return normalized
    except Exception:
        return build_affiliate_link(asin, partner_tag)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _select_listing_for_display(listings: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid: List[Dict[str, Any]] = []
    for listing in listings or []:
        amount = _safe_float((listing.get("price") or {}).get("money", {}).get("amount"))
        if not amount or amount <= 0:
            continue
        availability = str((listing.get("availability") or {}).get("type") or "").upper()
        if availability in {"OUT_OF_STOCK", "OUTOFSTOCK", "UNAVAILABLE"}:
            continue
        valid.append(listing)
    if not valid:
        return {}

    def is_subscribe(l: Dict[str, Any]) -> bool:
        normalized = str(l.get("type") or "").upper().replace("_", "")
        return normalized == "SUBSCRIBEANDSAVE"

    buy_box = [l for l in valid if l.get("isBuyBoxWinner") is True and not is_subscribe(l)]
    if buy_box:
        return buy_box[0]

    buy_box_any = [l for l in valid if l.get("isBuyBoxWinner") is True]
    if buy_box_any:
        return buy_box_any[0]

    return {}


def _creators_credentials() -> tuple[str, str, str]:
    cfg = _amazon_secrets()
    client_id = str(cfg.get("client_id") or cfg.get("credential_id") or "").strip()
    client_secret = str(cfg.get("client_secret") or cfg.get("credential_secret") or "").strip()
    token_url = str(cfg.get("token_url") or DEFAULT_EU_TOKEN_URL).strip()
    return client_id, client_secret, token_url


def _transient_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def get_creators_access_token(force_refresh: bool = False) -> Optional[str]:
    now = time.time()
    if (
        not force_refresh
        and _TOKEN_CACHE.get("access_token")
        and now < float(_TOKEN_CACHE.get("expires_at", 0)) - 60
    ):
        return str(_TOKEN_CACHE["access_token"])

    client_id, client_secret, token_url = _creators_credentials()
    if not client_id or not client_secret:
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creatorsapi::default",
    }

    for attempt in range(2):
        try:
            response = _HTTP_SESSION.post(
                token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            if attempt == 0:
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            return None

        if response.status_code == 200:
            try:
                data = response.json()
                token = data.get("access_token")
                if not token:
                    return None
                expires_in = int(data.get("expires_in", 3600))
                _TOKEN_CACHE["access_token"] = token
                _TOKEN_CACHE["expires_at"] = now + max(60, expires_in)
                return str(token)
            except (ValueError, TypeError):
                return None

        if _transient_status(response.status_code) and attempt == 0:
            time.sleep(RETRY_BACKOFF_SECONDS)
            continue
        return None

    return None


@st.cache_data(ttl=OFFERS_CACHE_TTL_SECONDS, show_spinner=False)
def _creators_api_call(operation: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    endpoint = f"{CREATORS_API_BASE}/{operation}"
    token = get_creators_access_token()
    if not token:
        return None

    transient_retry_used = False
    auth_refresh_used = False

    while True:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-marketplace": MARKETPLACE,
        }
        try:
            response = _HTTP_SESSION.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            if not transient_retry_used:
                transient_retry_used = True
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            return None

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                return None

        if response.status_code == 401 and not auth_refresh_used:
            auth_refresh_used = True
            _TOKEN_CACHE["access_token"] = None
            _TOKEN_CACHE["expires_at"] = 0.0
            token = get_creators_access_token(force_refresh=True)
            if not token:
                return None
            continue

        if _transient_status(response.status_code) and not transient_retry_used:
            transient_retry_used = True
            time.sleep(RETRY_BACKOFF_SECONDS)
            continue
        return None


def _api_item_to_product(
    item: Dict[str, Any],
    partner_tag: str,
    prime_filter_applied: bool = False,
) -> Optional[Dict[str, Any]]:
    asin = str(item.get("asin", "")).strip().upper()
    if len(asin) != 10:
        return None

    title = item.get("itemInfo", {}).get("title", {}).get("displayValue", "Prodotto Amazon")
    image_url = item.get("images", {}).get("primary", {}).get("large", {}).get("url", "")

    listings = item.get("offersV2", {}).get("listings", []) or []
    listing = _select_listing_for_display(listings)
    if not listing or listing.get("violatesMAP") is True:
        return None

    condition_value = str((listing.get("condition") or {}).get("value") or "").strip().upper()
    if condition_value and condition_value not in {"NEW", "NUOVO", "NUOVA"}:
        return None

    price_block = listing.get("price", {}) or {}
    money = price_block.get("money", {}) or {}
    price = _safe_float(money.get("amount")) or 0.0
    if price <= 0:
        return None
    price_display = str(money.get("displayAmount") or "").strip()

    saving_struct = price_block.get("savingBasis", {}) or {}
    saving_money = saving_struct.get("money", {}) or {}
    saving_basis = _safe_float(saving_money.get("amount"))
    saving_display = str(saving_money.get("displayAmount") or "").strip()

    savings_struct = price_block.get("savings", {}) or {}
    savings_pct = savings_struct.get("percentage")
    try:
        discount = int(round(float(savings_pct))) if savings_pct is not None else 0
    except (TypeError, ValueError):
        discount = 0

    has_reference_price = bool(saving_basis and saving_basis > price and discount > 0)
    old_price = float(saving_basis) if has_reference_price else float(price)
    if not has_reference_price:
        saving_display = ""

    if discount <= 0 and has_reference_price:
        discount = int(round(((old_price - price) / old_price) * 100))

    deal = listing.get("dealDetails", {}) or {}
    access_type = str(deal.get("accessType", "")).upper()
    is_prime_exclusive = "PRIME" in access_type
    is_prime = True if prime_filter_applied or is_prime_exclusive else None

    return {
        "asin": asin,
        "titolo": str(title or "Prodotto Amazon"),
        "immagine_url": str(image_url or ""),
        "prezzo_iniziale": old_price,
        "prezzo_finale": float(price),
        "prezzo_iniziale_display": saving_display,
        "prezzo_finale_display": price_display,
        "prezzo_verificato": True,
        "sconto": f"-{discount}%" if discount > 0 else "",
        "sconto_val": discount,
        "is_prime": is_prime,
        "is_sped_gratis": None,
        "costo_spedizione": None,
        "voto_medio": None,
        "num_recensioni": None,
        "link_affiliato": _affiliate_detail_url(item, asin, partner_tag),
    }


def _filter_verified_product(
    product: Dict[str, Any],
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    require_free_or_prime: bool = False,
) -> bool:
    if product.get("prezzo_verificato") is not True:
        return False
    price = float(product.get("prezzo_finale") or 0.0)
    discount = int(product.get("sconto_val") or 0)
    if price <= 0:
        return False
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    if discount < min_discount or discount > max_discount:
        return False
    if require_free_or_prime and product.get("is_prime") is not True and product.get("is_sped_gratis") is not True:
        return False
    return True


def _fetch_html(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> Optional[str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    cookies = {"lc-acbit": "it_IT", "i18n-prefs": "EUR", "sp-cdn": "L5Z9:IT"}

    if _CURL_SESSION is not None:
        try:
            response = _CURL_SESSION.get(url, headers=headers, cookies=cookies, timeout=timeout, impersonate="chrome")
            if response.status_code == 200 and response.text and len(response.text) > 1500 and "Robot Check" not in response.text:
                return response.text
        except Exception:
            pass

    try:
        response = _HTTP_SESSION.get(url, headers=headers, cookies=cookies, timeout=timeout)
        if response.status_code == 200 and response.text and len(response.text) > 1500 and "Robot Check" not in response.text:
            return response.text
    except requests.RequestException:
        pass
    return None


@st.cache_data(ttl=METADATA_CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_html_cached(url: str) -> Optional[str]:
    return _fetch_html(url)


def _extract_metadata_from_html(html_text: str, partner_tag: str) -> List[Dict[str, Any]]:
    if not html_text:
        return []
    soup = BeautifulSoup(html_text, "html.parser")
    items = soup.find_all("div", {"data-component-type": "s-search-result"})
    if not items:
        items = [
            div for div in soup.find_all("div", attrs={"data-asin": True})
            if len(div.get("data-asin", "").strip()) == 10
        ]

    products: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        asin = item.get("data-asin", "").strip().upper()
        if len(asin) != 10 or asin in seen:
            continue
        title_element = item.select_one("h2 span") or item.find("h2")
        if not title_element:
            continue
        title = title_element.get_text(" ", strip=True)
        image_element = item.select_one("img.s-image") or item.find("img")
        image_url = str(image_element.get("src") or image_element.get("data-src") or "") if image_element else ""
        seen.add(asin)
        products.append({
            "asin": asin,
            "titolo": title,
            "immagine_url": image_url,
            "prezzo_iniziale": None,
            "prezzo_finale": None,
            "prezzo_verificato": False,
            "sconto": "",
            "sconto_val": None,
            "is_prime": None,
            "is_sped_gratis": None,
            "costo_spedizione": None,
            "voto_medio": None,
            "num_recensioni": None,
            "link_affiliato": build_affiliate_link(asin, partner_tag),
        })
    return products


def _append_unique(target: List[Dict[str, Any]], source: Iterable[Dict[str, Any]], seen_asins: set[str], seen_titles: set[str]) -> None:
    for product in source:
        asin = str(product.get("asin", "")).strip().upper()
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', str(product.get("titolo", "")).lower())[:50]
        if asin and (asin not in seen_asins) and (clean_title not in seen_titles):
            seen_asins.add(asin)
            seen_titles.add(clean_title)
            target.append(product)


EXACT_ITEM_RESOURCES = [
    "images.primary.large",
    "itemInfo.title",
    "offersV2.listings.price",
    "offersV2.listings.dealDetails",
    "offersV2.listings.isBuyBoxWinner",
    "offersV2.listings.availability",
    "offersV2.listings.type",
    "offersV2.listings.merchantInfo",
    "offersV2.listings.condition",
    "offersV2.listings.violatesMAP",
]


def _get_exact_items_batch(
    asins: List[str],
    partner_tag: str,
    prime_filter_applied: bool = False,
) -> List[Dict[str, Any]]:
    clean_asins: List[str] = []
    seen: set[str] = set()
    for asin in asins:
        asin_clean = str(asin or "").strip().upper()
        if len(asin_clean) == 10 and asin_clean not in seen:
            seen.add(asin_clean)
            clean_asins.append(asin_clean)
    if not clean_asins:
        return []

    products: List[Dict[str, Any]] = []
    for start in range(0, len(clean_asins), 10):
        batch = clean_asins[start:start + 10]
        payload = {
            "itemIds": batch,
            "itemIdType": "ASIN",
            "marketplace": MARKETPLACE,
            "partnerTag": partner_tag,
            "languagesOfPreference": ["it_IT"],
            "currencyOfPreference": "EUR",
            "resources": EXACT_ITEM_RESOURCES,
        }
        data = _creators_api_call("getItems", payload)
        if not data:
            continue
        returned_items = data.get("itemsResult", {}).get("items", []) or []
        by_asin = {str(it.get("asin", "")).strip().upper(): it for it in returned_items}
        for asin in batch:
            item = by_asin.get(asin)
            if not item:
                continue
            product = _api_item_to_product(item, partner_tag, prime_filter_applied=prime_filter_applied)
            if product:
                products.append(product)
    return products


def _get_item_from_creators_api(
    asin: str,
    partner_tag: str,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    require_free_or_prime: bool = False,
) -> Optional[Dict[str, Any]]:
    products = _get_exact_items_batch([asin], partner_tag)
    if not products:
        return None
    product = products[0]
    return product if _filter_verified_product(
        product, min_price, max_price, min_discount, max_discount, require_free_or_prime
    ) else None


def _search_creators_api(
    keyword: str,
    sort_type: str,
    partner_tag: str,
    solo_spedizione_gratuita: bool,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    item_count: int,
) -> Optional[List[Dict[str, Any]]]:
    if not get_creators_access_token():
        return None

    sort_value = SORT_MAPPINGS.get(sort_type) or SORT_MAPPINGS.get(
        "Popolarità" if sort_type == "Numero di vendite" else sort_type,
        "Featured",
    )
    collected: List[Dict[str, Any]] = []
    seen_asins: set[str] = set()
    seen_titles: set[str] = set()
    pages_needed = min(MAX_CREATORS_PAGES, max(1, (item_count + 9) // 10))

    for page in range(1, pages_needed + 1):
        discovery_payload: Dict[str, Any] = {
            "partnerTag": partner_tag,
            "keywords": keyword,
            "searchIndex": "All",
            "marketplace": MARKETPLACE,
            "languagesOfPreference": ["it_IT"],
            "currencyOfPreference": "EUR",
            "itemCount": 10,
            "itemPage": page,
            "sortBy": sort_value,
            "resources": ["itemInfo.title"],
        }
        if min_price is not None:
            discovery_payload["minPrice"] = max(1, int(round(min_price * 100)))
        if max_price is not None:
            discovery_payload["maxPrice"] = max(1, int(round(max_price * 100)))
        if min_discount > 0:
            discovery_payload["minSavingPercent"] = min(99, int(min_discount))

        delivery_modes = ["Prime", "FreeShipping"] if solo_spedizione_gratuita else [None]
        page_had_items = False

        for delivery_mode in delivery_modes:
            mode_payload = dict(discovery_payload)
            if delivery_mode:
                mode_payload["deliveryFlags"] = [delivery_mode]

            data = _creators_api_call("searchItems", mode_payload)
            if data is None:
                return None if not collected else collected

            search_items = data.get("searchResult", {}).get("items", []) or []
            if search_items:
                page_had_items = True

            discovered_asins = [
                str(item.get("asin", "")).strip().upper()
                for item in search_items
                if len(str(item.get("asin", "")).strip()) == 10
            ]
            exact_products = _get_exact_items_batch(
                discovered_asins,
                partner_tag,
                prime_filter_applied=(delivery_mode == "Prime"),
            )
            parsed: List[Dict[str, Any]] = []
            for product in exact_products:
                if delivery_mode == "FreeShipping":
                    product["is_sped_gratis"] = True
                if _filter_verified_product(product, min_price, max_price, min_discount, max_discount):
                    parsed.append(product)
            _append_unique(collected, parsed, seen_asins, seen_titles)
            if len(collected) >= item_count:
                break

        if len(collected) >= item_count or not page_had_items:
            break

    if sort_type == "Prezzo minimo":
        collected.sort(key=lambda x: float(x.get("prezzo_finale") or float("inf")))

    return collected[:item_count]


def _search_html_fallback(
    keyword: str,
    sort_type: str,
    partner_tag: str,
    solo_spedizione_gratuita: bool,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    item_count: int,
) -> List[Dict[str, Any]]:
    if (
        solo_spedizione_gratuita
        or min_price is not None
        or max_price is not None
        or min_discount > 0
        or max_discount < 100
    ):
        return []

    query_encoded = urllib.parse.quote_plus(keyword)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "exact-aware-popularity-rank")
    collected: List[Dict[str, Any]] = []
    seen_asins: set[str] = set()
    seen_titles: set[str] = set()
    max_pages = min(4, max(1, (item_count + 15) // 16))

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.it/s?k={query_encoded}&page={page}&s={sort_param}"
        html_text = _fetch_html_cached(url)
        if not html_text:
            continue
        _append_unique(collected, _extract_metadata_from_html(html_text, partner_tag), seen_asins, seen_titles)
        if len(collected) >= item_count:
            break
    return collected[:item_count]


@st.cache_data(ttl=VETRINA_CACHE_TTL_SECONDS, show_spinner=False)
def ottieni_vetrina_casuale(partner_tag: Optional[str] = None, item_count: int = 10) -> List[Dict[str, Any]]:
    configured_tag = get_partner_tag() or str(partner_tag or "").strip()
    if not configured_tag:
        return []
    item_count = max(1, min(int(item_count or 10), 20))

    keyword = random.choice(KEYWORDS_VETRINA)
    products = ottieni_offerte_avanzate(
        keyword=keyword,
        sort_type="Popolarità",
        min_discount=5,
        item_count=min(MAX_RESULTS, item_count * 2),
        _partner_tag_override=configured_tag,
    )
    if not products:
        products = ottieni_offerte_avanzate(
            keyword="offerte del giorno",
            sort_type="Popolarità",
            min_discount=0,
            item_count=min(MAX_RESULTS, item_count * 2),
            _partner_tag_override=configured_tag,
        )
    if products:
        products = list(products)
        random.shuffle(products)
        return products[:item_count]
    return []


def ottieni_offerte_avanzate(
    keyword: str = "",
    sort_type: str = "Prezzo minimo",
    solo_spedizione_gratuita: bool = False,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_discount: int = 0,
    max_discount: int = 100,
    item_count: int = 10,
    categoria: str = "",
    sottocategoria: str = "",
    _partner_tag_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    del categoria, sottocategoria

    partner_tag = get_partner_tag() or str(_partner_tag_override or "").strip()
    if not partner_tag:
        return []

    item_count = max(1, min(int(item_count or 10), MAX_RESULTS))
    min_discount = max(0, min(int(min_discount or 0), 100))
    max_discount = max(min_discount, min(int(max_discount or 100), 100))
    clean_keyword = (keyword or "").strip()
    asin_match = RE_ASIN.search(clean_keyword)

    if asin_match and ("http" in clean_keyword.lower() or len(clean_keyword) == 10):
        asin = asin_match.group(1).upper()
        api_product = _get_item_from_creators_api(
            asin, partner_tag, min_price, max_price, min_discount, max_discount,
            require_free_or_prime=solo_spedizione_gratuita,
        )
        if api_product:
            return [api_product]

        fallback = _search_html_fallback(
            asin, "Popolarità", partner_tag, solo_spedizione_gratuita,
            min_price, max_price, min_discount, max_discount, 10,
        )
        for product in fallback:
            if product.get("asin") == asin:
                return [product]
        return []

    query = clean_keyword or "offerte del giorno"
    api_products = _search_creators_api(
        query, sort_type, partner_tag, solo_spedizione_gratuita,
        min_price, max_price, min_discount, max_discount, item_count,
    )
    if api_products is not None:
        return api_products[:item_count]

    return _search_html_fallback(
        query, sort_type, partner_tag, solo_spedizione_gratuita,
        min_price, max_price, min_discount, max_discount, item_count,
    )
